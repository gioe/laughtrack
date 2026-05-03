import XCTest

/// UI test that captures App Store screenshots in sequence.
///
/// Driven by fastlane's `snapshot` tool via the `screenshots` lane.
/// Run via: `bundle exec fastlane screenshots`
///
/// Mock-mode launch arg pre-populates the saved nearby ZIP to Hollywood (90028)
/// so the Near Me screen renders LA shows instead of leaking the runner's
/// IP-based geolocation into screenshots.
///
/// Screenshot order (matches fastlane/Framefile.json filters):
/// 1. Near Me        — Home tab, Hollywood location, LA shows
/// 2. Search Shows   — Search tab, Shows filter
/// 3. Search Comedians — Search tab, Comedians filter
/// 4. Search Clubs   — Search tab, Clubs filter
/// 5. Club Detail    — Laugh Factory Hollywood
/// 6. Show Detail    — A show at Laugh Factory
/// 7. Comedian Detail — Featured comedian profile
@MainActor
final class AppStoreScreenshotTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        setupSnapshot(app)
        app.launchArguments.append("-UITestMockMode")
        app.launch()
    }

    override func tearDownWithError() throws {
        app = nil
    }

    func testGenerateAllScreenshots() throws {
        let standardTimeout: TimeInterval = 15

        // 1. Near Me — first tab on launch
        XCTAssertTrue(
            app.staticTexts["TONIGHT"].waitForExistence(timeout: standardTimeout),
            "Near Me 'TONIGHT' header did not appear; the home rail likely failed to load."
        )
        snapshot("01_NearMe")

        // 2. Search → Shows (default filter)
        let searchTab = app.tabBars.buttons["Search"]
        XCTAssertTrue(searchTab.waitForExistence(timeout: standardTimeout))
        searchTab.tap()

        let searchShowsButton = app.buttons["laughtrack.primitive-filter.shows"]
        XCTAssertTrue(searchShowsButton.waitForExistence(timeout: standardTimeout))
        searchShowsButton.tap()
        sleep(2)
        snapshot("02_SearchShows")

        // 3. Search → Comedians
        app.buttons["laughtrack.primitive-filter.comedians"].tap()
        sleep(2)
        snapshot("03_SearchComedians")

        // 4. Search → Clubs
        app.buttons["laughtrack.primitive-filter.clubs"].tap()
        sleep(2)
        snapshot("04_SearchClubs")

        // 5. Club Detail — first club in the list
        let firstClub = app.buttons.matching(NSPredicate(format: "label CONTAINS 'shows' OR label CONTAINS 'comedians'")).firstMatch
        if firstClub.waitForExistence(timeout: standardTimeout) {
            firstClub.tap()
            sleep(2)
            snapshot("05_ClubDetail")

            // 6. Show Detail — first show row inside the club
            let firstShow = app.buttons.matching(NSPredicate(format: "label CONTAINS 'PM' OR label CONTAINS 'AM'")).firstMatch
            if firstShow.waitForExistence(timeout: standardTimeout) {
                firstShow.tap()
                sleep(2)
                snapshot("06_ShowDetail")

                // Back to club, back to clubs list
                app.navigationBars.buttons.firstMatch.tap()
                sleep(1)
            }
            app.navigationBars.buttons.firstMatch.tap()
            sleep(1)
        }

        // 7. Comedian Detail — switch to comedians filter and tap one
        app.buttons["laughtrack.primitive-filter.comedians"].tap()
        sleep(2)
        let firstComedian = app.buttons.matching(NSPredicate(format: "label CONTAINS 'upcoming shows'")).firstMatch
        if firstComedian.waitForExistence(timeout: standardTimeout) {
            firstComedian.tap()
            sleep(3)
            snapshot("07_ComedianDetail")
        }
    }
}
