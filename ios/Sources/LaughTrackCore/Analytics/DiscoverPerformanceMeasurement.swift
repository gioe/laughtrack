import Foundation
import OSLog
import HTTPTypes
import OpenAPIRuntime

/// Only bounded, explicitly named timing values may cross the analytics boundary.
public enum DiscoverPerformanceMetrics {
    public static let event = "discover_first_content"
    public static let providers: Set<String> = ["feed_total", "auth", "policy", "hero", "trending_comedians", "clubs", "comedians_near_you", "shows_tonight", "shows_near_zip", "trending_this_week", "podcast_episodes", "trending_podcasts", "followed_shows", "touring", "fresh", "affinity"]

    private static let logger = Logger(subsystem: "com.laughtrack.performance", category: "discover")

    /// Never fans out through identity-bearing AnalyticsManager/Firebase providers.
    public static func record(_ parameters: [String: Any]) {
        guard let safe = safeParameters(parameters),
              let data = try? JSONSerialization.data(withJSONObject: safe, options: [.sortedKeys]) else { return }
        logger.info("discover_first_content \(String(decoding: data, as: UTF8.self), privacy: .public)")
    }

    public static func safeParameters(_ parameters: [String: Any]) -> [String: Any]? {
        guard let source = parameters["source"] as? String,
              ["persisted_cache", "in_memory", "network"].contains(source),
              let account = parameters["account"] as? String,
              ["anonymous", "authenticated"].contains(account),
              let duration = parameters["first_content_ms"] as? Double,
              duration.isFinite, (0...120_000).contains(duration) else { return nil }
        var safe: [String: Any] = ["source": source, "account": account, "first_content_ms": duration]
        if source == "network" {
            let names = providers.map { "server_\($0)_ms" } + ["client_load_ms"]
            for name in names {
                if let value = parameters[name] as? Double, value.isFinite, (0...120_000).contains(value) {
                    safe[name] = value
                }
            }
        }
        return safe
    }

    public static func parse(_ header: String?) -> [String: Double] {
        guard let header, header.utf8.count <= 4096 else { return [:] }
        var result: [String: Double] = [:]
        for metric in header.split(separator: ",") {
            let parts = metric.split(separator: ";").map { $0.trimmingCharacters(in: .whitespaces) }
            guard let name = parts.first, providers.contains(name) else { continue }
            for part in parts.dropFirst() where part.hasPrefix("dur=") {
                if let value = Double(part.dropFirst(4)), value.isFinite, value >= 0, value <= 120_000 {
                    result["server_\(name)_ms"] = value
                }
            }
        }
        return result
    }
}

public actor DiscoverTimingCapture {
    @TaskLocal public static var current: DiscoverTimingCapture?
    private var values: [String: Double] = [:]
    public init() {}
    public func record(_ header: String?) { values = DiscoverPerformanceMetrics.parse(header) }
    public func snapshot() -> [String: Double] { values }
}

/// Captures only the final home-feed response in the requesting task's context.
public struct DiscoverTimingMiddleware: ClientMiddleware {
    public init() {}
    public func intercept(
        _ request: HTTPRequest, body: HTTPBody?, baseURL: URL, operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let result = try await next(request, body, baseURL)
        if operationID == "getHomeFeed", let capture = DiscoverTimingCapture.current {
            await capture.record(result.0.headerFields[HTTPField.Name("Server-Timing")!])
        }
        return result
    }
}
