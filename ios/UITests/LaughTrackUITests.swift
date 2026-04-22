import XCTest

final class LaughTrackUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    func testAppLaunchesAndDisplaysHomeView() throws {
        launchApp()

        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 5))
        XCTAssertTrue(app.staticTexts["Find comedy shows nearby"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Find shows"].exists)
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }

    func testNavigateToSettingsAndBack() throws {
        launchApp()

        openSettings()

        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Nearby defaults"].exists)

        app.navigationBars["Settings"].buttons.firstMatch.tap()

        XCTAssertTrue(app.staticTexts["Find comedy shows nearby"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
    }

    func testNearbyPreferencePersistsAcrossRelaunch() throws {
        launchApp(resetState: true)
        openSettings()

        XCTAssertTrue(app.staticTexts["No nearby preference saved"].waitForExistence(timeout: 3))

        let zipField = app.textFields["Saved ZIP code"]
        XCTAssertTrue(zipField.waitForExistence(timeout: 3))
        zipField.tap()
        zipField.typeText("10012")

        let distanceButton = app.buttons["50 mi"]
        XCTAssertTrue(distanceButton.waitForExistence(timeout: 3))
        distanceButton.tap()

        let saveButton = app.buttons["Save nearby preference"]
        XCTAssertTrue(saveButton.waitForExistence(timeout: 3))
        saveButton.tap()

        XCTAssertTrue(app.staticTexts["Nearby preference saved"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["ZIP 10012"].exists)
        XCTAssertTrue(app.staticTexts["50 mi"].exists)

        app.terminate()

        launchApp()
        openSettings()

        XCTAssertTrue(app.staticTexts["Nearby preference saved"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["ZIP 10012"].exists)
        XCTAssertTrue(app.staticTexts["50 mi"].exists)
        XCTAssertTrue(app.buttons["Clear nearby preference"].exists)
    }

    private func launchApp(resetState: Bool = false) {
        app = XCUIApplication()
        if resetState {
            app.launchArguments.append("UITEST_RESET_STATE")
        }
        app.launch()
    }

    private func openSettings() {
        let settingsButton = app.buttons["Settings"]
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 3))
        settingsButton.tap()
    }
}
