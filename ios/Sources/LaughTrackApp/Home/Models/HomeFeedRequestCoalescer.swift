import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

// Internal (not private) so tests can inject a fresh instance per test:
// the process-wide .shared instance coalesces by zip|distance key only, so
// concurrently-running test suites that refresh with the same key would
// otherwise receive each other's mock-transport feeds (TASK-2756).
struct MeasuredHomeFeedResult: Sendable {
    let result: Result<Components.Schemas.HomeFeed, LoadFailure>
    let serverTiming: [String: Double]
    let networkMilliseconds: Double
}

actor HomeFeedRequestCoalescer {
    static let shared = HomeFeedRequestCoalescer()

    private var inFlight: [String: Task<MeasuredHomeFeedResult, Never>] = [:]

    func load(
        requestKey: String,
        operation: @escaping @Sendable () async -> Result<Components.Schemas.HomeFeed, LoadFailure>
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        await loadMeasured(requestKey: requestKey, operation: operation).result
    }

    func loadMeasured(
        requestKey: String,
        operation: @escaping @Sendable () async -> Result<Components.Schemas.HomeFeed, LoadFailure>
    ) async -> MeasuredHomeFeedResult {
        if let task = inFlight[requestKey] {
            return await task.value
        }

        let task = Task {
            let capture = DiscoverTimingCapture()
            let start = ProcessInfo.processInfo.systemUptime
            let result = await DiscoverTimingCapture.$current.withValue(capture) { await operation() }
            return MeasuredHomeFeedResult(result: result, serverTiming: await capture.snapshot(),
                networkMilliseconds: min(120_000, max(0, (ProcessInfo.processInfo.systemUptime - start) * 1000)))
        }
        inFlight[requestKey] = task
        let result = await task.value
        inFlight[requestKey] = nil
        return result
    }
}

enum HomeFeedRequest {
    static func requestKey(
        zipCode: String?,
        distanceMiles: Int?,
        sessionDiscriminator: String? = nil
    ) -> String {
        let locationKey = "\(zipCode ?? "")|\(distanceMiles.map(String.init) ?? "")"
        guard let sessionDiscriminator else { return locationKey }
        return "\(sessionDiscriminator)|\(locationKey)"
    }

    static func load(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        sessionDiscriminator: String? = nil,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        await loadMeasured(apiClient: apiClient, zipCode: zipCode, distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator, cache: cache, cacheTTL: cacheTTL,
            badParamsMessage: badParamsMessage, rateLimitMessage: rateLimitMessage,
            undocumentedContext: undocumentedContext, networkContext: networkContext,
            networkMessage: networkMessage, persistentCache: persistentCache, coalescer: coalescer).result
    }

    static func loadMeasured(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        sessionDiscriminator: String? = nil,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer
    ) async -> MeasuredHomeFeedResult {
        await coalescer.loadMeasured(requestKey: requestKey(
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )) {
            await fetch(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                cacheTTL: cacheTTL,
                badParamsMessage: badParamsMessage,
                rateLimitMessage: rateLimitMessage,
                undocumentedContext: undocumentedContext,
                networkContext: networkContext,
                networkMessage: networkMessage,
                persistentCache: persistentCache
            )
        }
    }

    private static func fetch(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        do {
            let timezone = MockModeDetector.isMockMode
                ? "America/Los_Angeles"
                : TimeZone.autoupdatingCurrent.identifier
            let output = try await apiClient.getHomeFeed(
                .init(
                    query: .init(
                        zip: zipCode,
                        distance: zipCode == nil ? nil : distanceMiles,
                        platform: .ios
                    ),
                    headers: .init(xTimezone: timezone)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                await MainPageCache.set(
                    response.data,
                    forKey: .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
                    in: cache,
                    ttl: cacheTTL,
                    persistentCache: persistentCache
                )
                return .success(response.data)
            case .badRequest(let badRequest):
                return .failure(
                    .badParams((try? badRequest.body.json.error) ?? badParamsMessage)
                )
            case .tooManyRequests(let tooManyRequests):
                return .failure(
                    .rateLimited(retryAfter: nil, message: (try? tooManyRequests.body.json.error) ?? rateLimitMessage)
                )
            case .internalServerError(let serverError):
                return .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: undocumentedContext))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: networkContext,
                networkMessage: networkMessage
            ))
        }
    }
}
