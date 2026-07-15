import SharedKitTesting
import XCTest

/// UI test that captures App Store screenshots in sequence.
///
/// Driven by fastlane's `snapshot` tool via the `screenshots` lane:
/// `bundle exec fastlane screenshots`
///
/// Inherits boilerplate from `BaseAppStoreScreenshotTests` (XCUIApplication
/// setup and the `-UITestMockMode` launch argument).
/// Mock mode is wired in `LaughTrackApp.init` to seed the saved nearby ZIP
/// to Hollywood (90028) so the Near Me rail renders LA shows instead of
/// leaking the runner's IP-based geolocation.
@MainActor
final class AppStoreScreenshotTests: BaseAppStoreScreenshotTests {
    private enum Identifier {
        static let primitiveFilterScroller = "laughtrack.primitive-filter.scroller"
        static let clubDetailScreen = "laughtrack.club-detail.screen"
        static let showDetailScreen = "laughtrack.show-detail.screen"
        static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
        static let podcastDetailScreen = "laughtrack.podcast-detail-screen"
    }

    override func prepareForSnapshot() {
        setupSnapshot(app)
    }

    func testGenerateAllScreenshots() throws {
        // Time-based wait: the home rail loads from production API in ~3-5s.
        // SwiftUI's accessibility tree on iOS 18+ doesn't reliably surface
        // Text() views to XCUI's element queries, so we sleep instead.
        sleep(8)
        snapshot("01_NearMe")

        tapSearchTab()
        sleep(2)
        assertFirstResult(identifierPrefix: "laughtrack.shows-search.result-", description: "show")
        snapshot("02_SearchShows")

        // Filter pills sit at the top of the search header. Use identifiers
        // instead of coordinates so the flow survives pill-width changes.
        tapPrimitive("comedians")
        sleep(2)
        assertFirstResult(identifierPrefix: "laughtrack.comedians-search.result-", description: "comedian")
        snapshot("03_SearchComedians")

        tapPrimitive("clubs")
        sleep(2)
        assertFirstResult(identifierPrefix: "laughtrack.clubs-search.result-", description: "club")
        snapshot("04_SearchClubs")

        tapFirstResult(
            identifierPrefix: "laughtrack.clubs-search.result-",
            detailIdentifier: Identifier.clubDetailScreen,
            description: "club"
        )
        sleep(3)
        snapshot("05_ClubDetail")

        // The canonical Show Detail scenario is sourced from the first result
        // of Search Shows, independently of whichever club was captured above.
        relaunchOnSearchTab()
        tapFirstResult(
            identifierPrefix: "laughtrack.shows-search.result-",
            detailIdentifier: Identifier.showDetailScreen,
            description: "show"
        )
        sleep(3)
        snapshot("06_ShowDetail")

        // Restart before the remaining search-tab captures so the shared
        // search query is clear and the flow does not depend on back-stack
        // coordinates from the detail screens.
        relaunchOnSearchTab()

        // Switch to Comedians filter for the comedian detail.
        tapPrimitive("comedians")
        sleep(2)

        tapFirstResult(
            identifierPrefix: "laughtrack.comedians-search.result-",
            detailIdentifier: Identifier.comedianDetailScreen,
            description: "comedian"
        )
        sleep(3)
        snapshot("07_ComedianDetail")

        // Restart again before the podcast captures; the comedian detail has
        // its own Shows/Podcasts segmented control, so coordinate taps there
        // are not the global Search tab pivots.
        relaunchOnSearchTab()

        // Switch to Podcasts. The helper scrolls the identified primitive
        // scroller only when the pill is offscreen on the phone profile.
        tapPrimitive("podcasts")
        sleep(3)
        assertFirstResult(identifierPrefix: "laughtrack.podcasts-search.result-", description: "podcast")
        snapshot("08_SearchPodcasts")

        tapFirstResult(
            identifierPrefix: "laughtrack.podcasts-search.result-",
            detailIdentifier: Identifier.podcastDetailScreen,
            description: "podcast"
        )
        sleep(5)
        snapshot("09_PodcastDetail")
    }

    private func tapPrimitive(_ primitive: String) {
        let button = app.buttons["laughtrack.primitive-filter.\(primitive)"]
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Expected \(primitive) primitive filter")
        if !button.isHittable {
            let scroller = element(Identifier.primitiveFilterScroller)
            XCTAssertTrue(scroller.waitForExistence(timeout: 5), "Expected primitive filter scroller")
            for _ in 0..<3 where !button.isHittable {
                scroller.swipeLeft()
            }
        }
        XCTAssertTrue(button.isHittable, "Expected \(primitive) primitive filter to be hittable")
        button.tap()
    }

    private func tapSearchTab() {
        // SwiftUI renders TabView as a tab bar on iPhone and an adaptive
        // sidebar-style control on iPad. Query the semantic button directly
        // so the same navigation works in either container.
        let search = app.buttons["Search"]
        XCTAssertTrue(search.waitForExistence(timeout: 10), "Expected Search tab")
        search.tap()
    }

    private func relaunchOnSearchTab() {
        app.terminate()
        app.launch()
        sleep(5)
        tapSearchTab()
        sleep(2)
    }

    private func tapFirstResult(
        identifierPrefix: String,
        detailIdentifier: String,
        description: String
    ) {
        let result = firstResult(identifierPrefix: identifierPrefix)
        XCTAssertTrue(result.waitForExistence(timeout: 15), "Expected first \(description) result")
        XCTAssertTrue(result.isHittable, "Expected first \(description) result to be hittable")
        result.tap()
        assertExists(detailIdentifier, message: "Expected \(description) detail")
    }

    private func assertFirstResult(identifierPrefix: String, description: String) {
        XCTAssertTrue(
            firstResult(identifierPrefix: identifierPrefix).waitForExistence(timeout: 15),
            "Expected first \(description) result"
        )
    }

    private func firstResult(identifierPrefix: String) -> XCUIElement {
        let predicate = NSPredicate(format: "identifier BEGINSWITH %@", identifierPrefix)
        return app.descendants(matching: .any).matching(predicate).firstMatch
    }

    private func assertExists(_ identifier: String, message: String) {
        XCTAssertTrue(element(identifier).waitForExistence(timeout: 15), message)
    }

    private func element(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any)[identifier]
    }
}
