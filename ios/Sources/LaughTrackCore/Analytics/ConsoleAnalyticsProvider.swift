import Foundation
import LaughTrackBridge
import os

/// Logs analytics events to the unified logging system so they're visible in
/// Console.app during local development without touching production analytics.
///
/// Registered only in DEBUG builds — see `AppBootstrap.configureAnalytics`.
public final class ConsoleAnalyticsProvider: AnalyticsProvider {
    private let logger: Logger

    public init(subsystem: String = "com.laughtrack.analytics", category: String = "console") {
        self.logger = Logger(subsystem: subsystem, category: category)
    }

    public func track(_ event: AnalyticsEvent) {
        if let parameters = event.parameters, !parameters.isEmpty {
            logger.debug("event=\(event.name, privacy: .public) params=\(Self.describe(parameters), privacy: .public)")
        } else {
            logger.debug("event=\(event.name, privacy: .public)")
        }
    }

    public func trackScreen(_ name: String, parameters: [String: Any]?) {
        if let parameters, !parameters.isEmpty {
            logger.debug("screen=\(name, privacy: .public) params=\(Self.describe(parameters), privacy: .public)")
        } else {
            logger.debug("screen=\(name, privacy: .public)")
        }
    }

    public func setUserProperty(_ value: String?, forName name: String) {
        logger.debug("user_property name=\(name, privacy: .public) value=\(value ?? "<nil>", privacy: .private)")
    }

    public func setUserID(_ userID: String?) {
        logger.debug("user_id=\(userID ?? "<nil>", privacy: .private)")
    }

    public func reset() {
        logger.debug("reset")
    }

    private static func describe(_ parameters: [String: Any]) -> String {
        let pairs = parameters.keys.sorted().map { key in "\(key)=\(parameters[key] ?? "<nil>")" }
        return "[" + pairs.joined(separator: ", ") + "]"
    }
}
