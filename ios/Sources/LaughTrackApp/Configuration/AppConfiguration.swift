import Foundation

enum AppConfiguration {
    /// Base URL for the API backend.
    /// Update this to point to your actual server.
    static let apiBaseURL = URL(string: "https://laughtrack.app/api/v1")!

    /// Bundle identifier
    static let bundleID = "com.laughtrack.laughtrack"
}
