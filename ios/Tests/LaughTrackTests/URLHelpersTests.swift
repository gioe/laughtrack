import Foundation
import Testing
import LaughTrackCore
@testable import LaughTrackApp

@Suite("URL helpers")
struct URLHelpersTests {
    @Test("root-relative API URLs resolve against the configured app host")
    func rootRelativeAPIURLsResolveAgainstAppHost() {
        let url = URL.normalizedExternalURL("/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fart.jpg")

        #expect(url?.scheme == AppConfiguration.apiBaseURL.scheme)
        #expect(url?.host == AppConfiguration.apiBaseURL.host)
        #expect(url?.path == "/api/v1/podcast-artwork")
        #expect(url?.query == "url=https%3A%2F%2Fcdn.example.com%2Fart.jpg")
    }

    @Test("absolute and host-only external URLs keep existing behavior")
    func absoluteAndHostOnlyURLsKeepExistingBehavior() {
        #expect(URL.normalizedExternalURL("https://example.com/show") == URL(string: "https://example.com/show"))
        #expect(URL.normalizedExternalURL("example.com/show") == URL(string: "https://example.com/show"))
    }
}
