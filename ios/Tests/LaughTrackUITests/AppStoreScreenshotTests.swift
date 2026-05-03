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

        // Filter pills sit at the top of the search header.
        // Centers from accessibility frames: Shows ~105, Comedians ~188, Clubs ~270 at y~69.
        tap(x: 188, y: 69)
        sleep(2)
        snapshot("03_SearchComedians")

        tap(x: 270, y: 69)
        sleep(2)
        snapshot("04_SearchClubs")

        // Tap the first club row. The list scrolls below the filter chips
        // (sort, distance pills, "Showing N of M") so the first card sits
        // around y=520 on iPhone 16 Pro Max.
        tap(x: 220, y: 525)
        sleep(3)
        snapshot("05_ClubDetail")

        // Tap the first show row inside the club detail. Show rows render
        // below the venue header / website / maps row / sort+filter row.
        tap(x: 220, y: 615)
        sleep(3)
        snapshot("06_ShowDetail")

        // Back to club, back to clubs list — navbar back button at ~(35, 75).
        tap(x: 35, y: 75)
        sleep(1)
        tap(x: 35, y: 75)
        sleep(2)

        // Switch to Comedians filter for the comedian detail.
        tap(x: 188, y: 69)
        sleep(2)

        // Tap the first comedian row.
        tap(x: 220, y: 525)
        sleep(3)
        snapshot("07_ComedianDetail")
    }
}
