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
        XCTAssertTrue(app.staticTexts["Find comedy shows nearby"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Find shows"].exists)
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }

    func testNavigateToSettingsAndBack() throws {
        let settingsButton = app.buttons["Settings"]
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 3))
        settingsButton.tap()

        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Nearby discovery"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["No nearby ZIP is saved yet."].exists)

        app.navigationBars["Settings"].buttons.firstMatch.tap()

        XCTAssertTrue(app.staticTexts["Find comedy shows nearby"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }
}
