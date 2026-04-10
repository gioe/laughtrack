import XCTest

final class LaughTrackUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()
    }

    func testAppLaunchesAndDisplaysHomeView() throws {
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 5))
        XCTAssertTrue(app.staticTexts["Welcome to LaughTrack"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }

    func testNavigateToSettingsAndBack() throws {
        let settingsButton = app.buttons["Settings"]
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 3))
        settingsButton.tap()

        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Settings"].exists)

        app.navigationBars["Settings"].buttons.firstMatch.tap()

        XCTAssertTrue(app.staticTexts["Welcome to LaughTrack"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }
}
