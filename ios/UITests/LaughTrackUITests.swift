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
        XCTAssertTrue(app.navigationBars["LaughTrack"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["What’s funny near New York tonight?"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }

    func testNavigateToSettingsAndBack() throws {
        let settingsButton = app.buttons["Open settings"]
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 3))
        settingsButton.tap()

        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Discovery"].waitForExistence(timeout: 3))

        app.navigationBars["Settings"].buttons.firstMatch.tap()

        XCTAssertTrue(app.staticTexts["What’s funny near New York tonight?"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }
}
