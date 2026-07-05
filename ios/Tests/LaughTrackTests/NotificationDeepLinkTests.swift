import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Notification deep links")
struct NotificationDeepLinkTests {
    @Test("payload showId opens show detail")
    func payloadShowIDOpensShowDetail() {
        #expect(
            LaughTrackNotificationDeepLink.route(from: ["showId": 2993368]) == .showDetail(2993368)
        )
    }

    @Test("string payload showId opens show detail")
    func stringPayloadShowIDOpensShowDetail() {
        #expect(
            LaughTrackNotificationDeepLink.route(from: ["showId": "2993368"]) == .showDetail(2993368)
        )
    }

    @Test("payload URL falls back to show detail route")
    func payloadURLFallsBackToShowDetailRoute() throws {
        #expect(
            LaughTrackNotificationDeepLink.route(from: [
                "url": "https://laugh-track.com/show/2993368"
            ]) == .showDetail(2993368)
        )
    }

    @Test("custom app show URL opens show detail")
    func customAppShowURLOpensShowDetail() throws {
        let url = try #require(URL(string: "laughtrack://show/2993368"))

        #expect(LaughTrackNotificationDeepLink.route(from: url) == .showDetail(2993368))
    }

    @Test("payload route=favorites opens the favorites tab")
    func payloadRouteFavoritesOpensLibrary() {
        #expect(LaughTrackNotificationDeepLink.route(from: ["route": "favorites"]) == .library)
    }

    @Test("grouped push route wins over the showId fallback")
    func routeTakesPrecedenceOverShowIDFallback() {
        #expect(
            LaughTrackNotificationDeepLink.route(from: [
                "route": "favorites",
                "showId": 2993368,
            ]) == .library
        )
    }

    @Test("notification image URL key is recognized")
    func notificationImageURLKeyIsRecognized() throws {
        let url = try #require(LaughTrackNotificationMedia.imageURL(from: [
            "imageUrl": "https://laughtrack.b-cdn.net/comedians/Steve%20Furey.png"
        ]))

        #expect(url.absoluteString == "https://laughtrack.b-cdn.net/comedians/Steve%20Furey.png")
    }
}
