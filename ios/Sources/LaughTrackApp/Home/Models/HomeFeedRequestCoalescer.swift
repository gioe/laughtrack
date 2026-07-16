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
actor HomeFeedRequestCoalescer {
    static let shared = HomeFeedRequestCoalescer()

    private var inFlight: [String: Task<Result<Components.Schemas.HomeFeed, LoadFailure>, Never>] = [:]

    func load(
        requestKey: String,
        operation: @escaping @Sendable () async -> Result<Components.Schemas.HomeFeed, LoadFailure>
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        if let task = inFlight[requestKey] {
            return await task.value
        }

        let task = Task {
            await operation()
        }
        inFlight[requestKey] = task
        let result = await task.value
        inFlight[requestKey] = nil
        return result
    }
}

enum HomeFeedRequest {
    static func requestKey(zipCode: String?, distanceMiles: Int?) -> String {
        "\(zipCode ?? "")|\(distanceMiles.map(String.init) ?? "")"
    }

    static func load(
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
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        await coalescer.load(requestKey: requestKey(zipCode: zipCode, distanceMiles: distanceMiles)) {
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
                    query: .init(zip: zipCode, distance: zipCode == nil ? nil : distanceMiles),
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
