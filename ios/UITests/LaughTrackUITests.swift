import XCTest

final class LaughTrackUITests: XCTestCase {
    private enum ViewID {
        static let homeScreen = "laughtrack.home.screen"
        static let homeSettingsButton = "laughtrack.home.settings-button"
        static let settingsScreen = "laughtrack.settings.screen"
        static let settingsNearbyEmptyState = "laughtrack.settings.nearby.empty-state"
        static let settingsNearbySavedState = "laughtrack.settings.nearby.saved-state"
        static let settingsZipField = "laughtrack.settings.zip-field"
        static let settingsDistancePicker = "laughtrack.settings.distance-picker"
        static let settingsSaveButton = "laughtrack.settings.save-button"
        static let settingsClearButton = "laughtrack.settings.clear-button"
    }

    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    func testAppLaunchesAndDisplaysMajorHomeSections() throws {
        launchApp(resetState: true)

        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 5))
        XCTAssertTrue(element(matching: ViewID.homeScreen).waitForExistence(timeout: 3))
        XCTAssertTrue(app.navigationBars["LaughTrack"].exists)
        XCTAssertTrue(button(matching: ViewID.homeSettingsButton).exists)

        assertHomeSectionsVisible()
    }

    func testSettingsFlowOpensAndReturnsToHome() throws {
        launchApp(resetState: true)

        openSettings()
        assertSettingsScreenVisible()

        navigateBackToHome()

        XCTAssertTrue(element(matching: ViewID.homeScreen).waitForExistence(timeout: 3))
        assertHomeSectionsVisible()
    }

    func testSettingsScreenRendersPrimarySectionsAndControls() throws {
        launchApp(resetState: true)
        openSettings()
        assertSettingsScreenVisible()

        XCTAssertTrue(element(matching: ViewID.settingsNearbyEmptyState).waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Nearby defaults"].exists)
        XCTAssertTrue(app.staticTexts["Edit nearby preference"].exists)
        XCTAssertTrue(app.textFields[ViewID.settingsZipField].exists)
        XCTAssertTrue(element(matching: ViewID.settingsDistancePicker).exists)
        XCTAssertTrue(button(matching: ViewID.settingsSaveButton).exists)
        XCTAssertTrue(app.staticTexts["Push notifications are not available yet"].exists)
        XCTAssertTrue(app.staticTexts["LaughTrack account"].exists)
        XCTAssertTrue(app.staticTexts["What this enables"].exists)
    }

    func testNearbyPreferenceControlsUpdateUiConsistently() throws {
        launchApp(resetState: true)
        openSettings()

        XCTAssertTrue(element(matching: ViewID.settingsNearbyEmptyState).waitForExistence(timeout: 3))

        let zipField = app.textFields[ViewID.settingsZipField]
        XCTAssertTrue(zipField.waitForExistence(timeout: 3))
        zipField.tap()
        zipField.typeText("10012")

        let distanceButton = app.buttons["50 mi"]
        XCTAssertTrue(distanceButton.waitForExistence(timeout: 3))
        distanceButton.tap()

        let saveButton = button(matching: ViewID.settingsSaveButton)
        XCTAssertTrue(saveButton.waitForExistence(timeout: 3))
        saveButton.tap()

        XCTAssertTrue(element(matching: ViewID.settingsNearbySavedState).waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["ZIP 10012"].exists)
        XCTAssertTrue(app.staticTexts["50 mi"].exists)
        XCTAssertTrue(button(matching: ViewID.settingsClearButton).exists)

        let updatedDistanceButton = app.buttons["5 mi"]
        XCTAssertTrue(updatedDistanceButton.waitForExistence(timeout: 3))
        updatedDistanceButton.tap()
        saveButton.tap()

        XCTAssertTrue(app.staticTexts["5 mi"].waitForExistence(timeout: 3))

        let clearButton = button(matching: ViewID.settingsClearButton)
        XCTAssertTrue(clearButton.waitForExistence(timeout: 3))
        clearButton.tap()

        XCTAssertTrue(element(matching: ViewID.settingsNearbyEmptyState).waitForExistence(timeout: 3))
        XCTAssertFalse(button(matching: ViewID.settingsClearButton).exists)
    }

    func testNearbyPreferencePersistsAcrossRelaunch() throws {
        launchApp(resetState: true)
        openSettings()

        XCTAssertTrue(element(matching: ViewID.settingsNearbyEmptyState).waitForExistence(timeout: 3))

        let zipField = app.textFields[ViewID.settingsZipField]
        XCTAssertTrue(zipField.waitForExistence(timeout: 3))
        zipField.tap()
        zipField.typeText("10012")

        let distanceButton = app.buttons["50 mi"]
        XCTAssertTrue(distanceButton.waitForExistence(timeout: 3))
        distanceButton.tap()

        let saveButton = button(matching: ViewID.settingsSaveButton)
        XCTAssertTrue(saveButton.waitForExistence(timeout: 3))
        saveButton.tap()

        XCTAssertTrue(element(matching: ViewID.settingsNearbySavedState).waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["ZIP 10012"].exists)
        XCTAssertTrue(app.staticTexts["50 mi"].exists)

        app.terminate()

        launchApp()
        openSettings()

        XCTAssertTrue(element(matching: ViewID.settingsNearbySavedState).waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["ZIP 10012"].exists)
        XCTAssertTrue(app.staticTexts["50 mi"].exists)
        XCTAssertTrue(button(matching: ViewID.settingsClearButton).exists)
    }

    private func launchApp(resetState: Bool = false) {
        app = XCUIApplication()
        if resetState {
            app.launchArguments.append("UITEST_RESET_STATE")
        }
        app.launch()
    }

    private func openSettings() {
        let settingsButton = button(matching: ViewID.homeSettingsButton)
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 3))
        settingsButton.tap()
    }

    private func navigateBackToHome() {
        let backButton = app.navigationBars["Settings"].buttons.firstMatch
        XCTAssertTrue(backButton.waitForExistence(timeout: 3))
        backButton.tap()
    }

    private func assertHomeSectionsVisible() {
        XCTAssertTrue(app.staticTexts["Find comedy shows nearby"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.staticTexts["Nearby tonight"].exists)
        XCTAssertTrue(app.staticTexts["Find shows"].exists)
        XCTAssertTrue(app.staticTexts["Search comedians"].exists)
        XCTAssertTrue(app.staticTexts["Search clubs"].exists)
    }

    private func assertSettingsScreenVisible() {
        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 3))
        XCTAssertTrue(element(matching: ViewID.settingsScreen).exists)
    }

    private func element(matching identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    private func button(matching identifier: String) -> XCUIElement {
        app.buttons.matching(identifier: identifier).firstMatch
    }
}
