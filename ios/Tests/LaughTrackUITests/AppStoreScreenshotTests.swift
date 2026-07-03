import SharedKitTesting
import XCTest

/// UI test that captures App Store screenshots in sequence.
///
/// Driven by fastlane's `snapshot` tool via the `screenshots` lane:
/// `bundle exec fastlane screenshots`
///
/// Inherits boilerplate from `BaseAppStoreScreenshotTests` (XCUIApplication
/// setup, `-UITestMockMode` launch arg, coordinate-based `tap(x:y:)` helper).
/// Mock mode is wired in `LaughTrackApp.init` to seed the saved nearby ZIP
/// to Hollywood (90028) so the Near Me rail renders LA shows instead of
/// leaking the runner's IP-based geolocation.
///
/// Coordinates are hardcoded for iPhone 16 Pro Max (440×956 logical points).
@MainActor
final class AppStoreScreenshotTests: BaseAppStoreScreenshotTests {
    override func prepareForSnapshot() {
        setupSnapshot(app)
    }

    func testGenerateAllScreenshots() throws {
        // Time-based wait: the home rail loads from production API in ~3-5s.
        // SwiftUI's accessibility tree on iOS 18+ doesn't reliably surface
        // Text() views to XCUI's element queries, so we sleep instead.
        sleep(8)
        snapshot("01_NearMe")

        // Tab bar: 3 tabs at bottom of 956pt screen, ~y=915 in 440pt-wide layout.
        // Centers: Near Me ~73, Search ~220, Favorites ~367.
        tap(x: 220, y: 915)
        sleep(2)
        snapshot("02_SearchShows")

        // Filter pills sit at the top of the search header. Use identifiers
        // instead of coordinates so the flow survives pill-width changes.
        tapPrimitive("comedians")
        sleep(2)
        snapshot("03_SearchComedians")

        tapPrimitive("clubs")
        sleep(2)
        snapshot("04_SearchClubs")

        // App Store screenshots should feature The Comedy Store instead of
        // whichever LA/SF venue happens to sort first in production.
        searchFor("Comedy Store")
        tapButton(containingLabel: "The Comedy Store")
        sleep(3)
        snapshot("05_ClubDetail")

        // Nested show rows on club detail do not expose the search-result
        // button identifier in the UI-test accessibility tree; the first
        // Comedy Store show row is visible below the calendar controls.
        tap(x: 220, y: 665)
        sleep(3)
        snapshot("06_ShowDetail")

        // Restart before the remaining search-tab captures so the shared
        // search query is clear and the flow does not depend on back-stack
        // coordinates from the detail screens.
        app.terminate()
        app.launch()
        sleep(5)
        tap(x: 220, y: 915)
        sleep(2)

        // Switch to Comedians filter for the comedian detail.
        tapPrimitive("comedians")
        sleep(2)

        // Tap the first comedian row.
        tap(x: 220, y: 525)
        sleep(3)
        snapshot("07_ComedianDetail")

        // Restart again before the podcast captures; the comedian detail has
        // its own Shows/Podcasts segmented control, so coordinate taps there
        // are not the global Search tab pivots.
        app.terminate()
        app.launch()
        sleep(5)
        tap(x: 220, y: 915)
        sleep(2)

        // Switch to Podcasts pill (the 4th pivot, only rendered on the Search
        // tab). It starts partially offscreen on iPhone 16 Pro Max, so reveal
        // it before tapping by identifier.
        scrollPrimitiveFiltersLeft()
        tapPrimitive("podcasts")
        sleep(3)
        snapshot("08_SearchPodcasts")

        // Tap the first podcast row. Mirrors the comedian/club row offset on
        // the search list (~y=525 below the search header + sort/filter row).
        tap(x: 220, y: 525)
        sleep(5)
        snapshot("09_PodcastDetail")
    }

    private func searchFor(_ query: String) {
        let field = app.textFields["laughtrack.search.field"]
        if field.waitForExistence(timeout: 5) {
            field.tap()
            field.typeText(query)
        } else {
            // SwiftUI's accessibility tree is inconsistent for the custom root
            // search field on CI simulators; the field is visually stable.
            tap(x: 220, y: 150)
            app.typeText(query)
        }
        sleep(3)
    }

    private func tapButton(containingLabel text: String) {
        let predicate = NSPredicate(format: "label CONTAINS[c] %@", text)
        let button = app.buttons.matching(predicate).firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Expected button containing label '\(text)'")
        button.tap()
    }

    private func tapPrimitive(_ primitive: String) {
        let button = app.buttons["laughtrack.primitive-filter.\(primitive)"]
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Expected \(primitive) primitive filter")
        button.tap()
    }

    private func scrollPrimitiveFiltersLeft() {
        let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.93, dy: 0.07))
        let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.45, dy: 0.07))
        start.press(forDuration: 0.1, thenDragTo: end)
        sleep(1)
    }
}
