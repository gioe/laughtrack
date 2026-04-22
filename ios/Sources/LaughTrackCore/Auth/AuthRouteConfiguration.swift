import Foundation

public enum AuthRouteConfiguration {
    public static let callbackScheme = "laughtrack"
    public static let websiteBaseURL = URL(string: "https://laughtrack.app")!

    public static func nativeCallbackURL(for provider: AuthProvider) -> URL {
        var components = URLComponents(
            url: websiteBaseURL
                .appendingPathComponent("api")
                .appendingPathComponent("v1")
                .appendingPathComponent("auth")
                .appendingPathComponent("native")
                .appendingPathComponent("callback"),
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = [
            URLQueryItem(name: "provider", value: provider.rawValue)
        ]
        return components.url!
    }

    public static func signInURL(for provider: AuthProvider) -> URL {
        var components = URLComponents(
            url: websiteBaseURL
                .appendingPathComponent("api")
                .appendingPathComponent("auth")
                .appendingPathComponent("signin")
                .appendingPathComponent(provider.rawValue),
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = [
            URLQueryItem(name: "callbackUrl", value: nativeCallbackURL(for: provider).absoluteString)
        ]
        return components.url!
    }
}
