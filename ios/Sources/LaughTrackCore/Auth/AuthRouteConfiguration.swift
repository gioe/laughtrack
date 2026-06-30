import Foundation

public enum AuthRouteConfiguration {
    public static let callbackScheme = "laughtrack"
    public static var websiteBaseURL: URL { AppConfiguration.apiBaseURL }

    // `state` is the per-flow CSRF nonce minted by AuthManager. It rides on the
    // callbackUrl so the web native-callback route round-trips it back on the
    // laughtrack:// redirect, where AuthManager verifies it (mirrors the Android
    // AuthSessionManager flow shipped in TASK-3271).
    public static func nativeCallbackURL(for provider: AuthProvider, state: String? = nil) -> URL {
        var components = URLComponents(
            url: websiteBaseURL
                .appendingPathComponent("api")
                .appendingPathComponent("v1")
                .appendingPathComponent("auth")
                .appendingPathComponent("native")
                .appendingPathComponent("callback"),
            resolvingAgainstBaseURL: false
        )!
        var items = [URLQueryItem(name: "provider", value: provider.rawValue)]
        if let state {
            items.append(URLQueryItem(name: "state", value: state))
        }
        components.queryItems = items
        return components.url!
    }

    public static func signInURL(for provider: AuthProvider, state: String? = nil) -> URL {
        var components = URLComponents(
            url: websiteBaseURL,
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = [
            URLQueryItem(
                name: "callbackUrl",
                value: nativeCallbackURL(for: provider, state: state).absoluteString
            ),
            URLQueryItem(name: "nativeAuthProvider", value: provider.rawValue)
        ]
        return components.url!
    }
}

#if DEBUG
public struct DebugTestAuthConfiguration: Equatable, Sendable {
    public let email: String
    public let secret: String
    public let endpointURL: URL

    public static func resolve(
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> DebugTestAuthConfiguration? {
        let email = trimmed(
            environment["LAUGHTRACK_TEST_AUTH_EMAIL"]
        ) ?? "admin@laugh-track.com"
        guard let secret = trimmed(environment["LAUGHTRACK_TEST_AUTH_SECRET"]) else {
            return nil
        }
        return DebugTestAuthConfiguration(
            email: email,
            secret: secret,
            endpointURL: AuthRouteConfiguration.websiteBaseURL
                .appendingPathComponent("api")
                .appendingPathComponent("v1")
                .appendingPathComponent("auth")
                .appendingPathComponent("test-token")
        )
    }

    private static func trimmed(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
#endif
