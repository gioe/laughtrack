import Foundation

public enum AppConfiguration {
    /// Base URL for the LaughTrack web host.
    ///
    /// The OpenAPI client emits absolute operation paths, so the app injects the
    /// `/api/v1` mount point in middleware and keeps the configured base URL at
    /// the host root. The simulator can override this at runtime for local
    /// verification while production launches continue to default to the hosted
    /// LaughTrack web domain.
    public static let apiBaseURL: URL = {
        if
            let override = ProcessInfo.processInfo.environment["LAUGHTRACK_API_BASE_URL"],
            let url = URL(string: override)
        {
            return url
        }

        return URL(string: "https://www.laugh-track.com")!
    }()

    public static var sentryDSN: String? {
        sentryDSN(
            infoDictionary: Bundle.main.infoDictionary,
            environment: ProcessInfo.processInfo.environment
        )
    }

    public static func sentryDSN(
        infoDictionary: [String: Any]?,
        environment: [String: String]
    ) -> String? {
        let rawValue = environment["SENTRY_DSN"] ?? infoDictionary?["SentryDSN"] as? String
        guard let value = nonPlaceholderValue(rawValue) else { return nil }
        return value
    }

    public static var sentryReleaseIdentifier: String {
        sentryReleaseIdentifier(infoDictionary: Bundle.main.infoDictionary)
    }

    public static func sentryReleaseIdentifier(infoDictionary: [String: Any]?) -> String {
        let bundleIdentifier = nonPlaceholderValue(infoDictionary?["CFBundleIdentifier"] as? String) ?? "app.laughtrack.ios"
        let marketingVersion = nonPlaceholderValue(infoDictionary?["CFBundleShortVersionString"] as? String) ?? "0"
        let buildNumber = sentryBuildNumber(infoDictionary: infoDictionary)
        return "\(bundleIdentifier)@\(marketingVersion)+\(buildNumber)"
    }

    public static var sentryBuildNumber: String {
        sentryBuildNumber(infoDictionary: Bundle.main.infoDictionary)
    }

    public static func sentryBuildNumber(infoDictionary: [String: Any]?) -> String {
        nonPlaceholderValue(infoDictionary?["CFBundleVersion"] as? String) ?? "0"
    }

    public static var sentryEnvironment: String {
        if let override = nonPlaceholderValue(ProcessInfo.processInfo.environment["SENTRY_ENVIRONMENT"]) {
            return override
        }

        #if DEBUG
        return "development"
        #else
        return "production"
        #endif
    }

    private static func nonPlaceholderValue(_ rawValue: String?) -> String? {
        guard let rawValue else { return nil }
        let value = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, !value.hasPrefix("$(") else { return nil }
        return value
    }
}
