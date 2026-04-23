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
}
