import Foundation
import XCTest
import UIKit

/// Real navigation, populated by scripts/screenshots/fixture_server.py. No mock
/// navigation root or forced full-screen player: only data and paused playback
/// are seeded. Run these cases at native default/large text and Reduce Motion.
@MainActor
final class NavigationTransitionUITests: XCTestCase {
    func testTabsAndInteractiveBackRetainExactDiscoverPosition() throws {
        let app = try launchApp(seedPlayer: true)
        defer { app.terminate() }
        let home = element("laughtrack.home.screen", in: app)
        XCTAssertTrue(home.waitForExistence(timeout: 15))
        let marker = element("laughtrack.home.this-week-rail", in: app)
        XCTAssertTrue(marker.waitForExistence(timeout: 15))
        position(marker, at: home.frame.minY + 85, in: app)
        let originalY = marker.frame.minY
        let originalPlayerY = element("laughtrack.podcast-mini-player", in: app).frame.minY
        XCTAssertLessThan(originalY, home.frame.minY + 150, "Test must leave Discover genuinely scrolled")
        attach(app, "Discover — retained position")

        for _ in 0..<2 {
            app.tabBars.buttons["Search"].tap()
            XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
            let comedians = app.buttons["laughtrack.primitive-filter.comedians"]
            XCTAssertTrue(comedians.waitForExistence(timeout: 5))
            comedians.tap()
            app.tabBars.buttons["Library"].tap()
            XCTAssertTrue(app.tabBars.buttons["Library"].isSelected)
            app.tabBars.buttons["Discover"].tap()
            assertPosition(marker, y: originalY)
        }
        attach(app, "Discover — after rapid tabs and Search pivot")

        let show = element("laughtrack.home.shows-tonight-103", in: app)
        XCTAssertTrue(show.isHittable, "Fixture show must be reachable at the retained scroll position")
        show.tap()
        let detail = element("laughtrack.show-detail.screen", in: app)
        XCTAssertTrue(detail.waitForExistence(timeout: 10))
        let detailFrame = detail.frame
        attach(app, "Show — pushed")

        // A slow short edge drag settles back to the detail; a subsequent long
        // edge drag commits the actual UIKit interactive pop (no Back tap).
        edgeDrag(in: app, to: 0.16)
        XCTAssertTrue(detail.exists, "Cancelling interactive back must retain the detail")
        XCTAssertEqual(detail.frame.minX, detailFrame.minX, accuracy: 3)
        XCTAssertEqual(detail.frame.minY, detailFrame.minY, accuracy: 3)
        attach(app, "Show — cancelled interactive back")
        edgeDrag(in: app, to: 0.88)
        XCTAssertTrue(home.waitForExistence(timeout: 5), "A committed native edge gesture must pop the detail")
        XCTAssertFalse(detail.exists)
        XCTAssertTrue(app.tabBars.buttons["Discover"].isSelected)
        assertPosition(marker, y: originalY)
        XCTAssertEqual(element("laughtrack.podcast-mini-player", in: app).frame.minY, originalPlayerY, accuracy: 3)
        attach(app, "Discover — committed interactive back")
    }

    func testNativePlayerSheetAuthDismissalAndResumeRetainSearch() throws {
        try verifyPlayerAndModalContinuity()
    }

    func testLargeTextKeepsPlayerControlsAndDismissalReachable() throws {
        try verifyPlayerAndModalContinuity(largeText: true)
    }

    func testNativeReduceMotionRetainsPlayerModalAndResumeContinuity() throws {
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        for _ in 0..<5 { settings.swipeDown() }
        let accessibility = settings.staticTexts["Accessibility"].firstMatch
        for _ in 0..<8 where !accessibility.isHittable { settings.swipeUp() }
        XCTAssertTrue(accessibility.waitForExistence(timeout: 5))
        accessibility.tap()
        settings.staticTexts["Motion"].firstMatch.tap()
        let toggle = settings.switches["Reduce Motion"]
        XCTAssertTrue(toggle.waitForExistence(timeout: 5))
        let originallyEnabled = toggle.value as? String == "1"
        if !originallyEnabled { toggle.tap() }
        XCTAssertEqual(toggle.value as? String, "1")
        defer {
            settings.activate()
            if (toggle.value as? String == "1") != originallyEnabled { toggle.tap() }
            settings.terminate()
        }
        try verifyPlayerAndModalContinuity()
    }

    // Requires the documented test-only TARGETED_DEVICE_FAMILY=1,2 build.
    func testTabletPlayerKeepsControlsAndCloseReachable() throws {
        try XCTSkipUnless(UIDevice.current.userInterfaceIdiom == .pad, "Regular-width player is verified on iPad")
        let app = try launchApp(seedPlayer: true)
        defer { app.terminate() }
        let mini = element("laughtrack.podcast-mini-player", in: app)
        XCTAssertTrue(mini.waitForExistence(timeout: 5))
        expandPlayer(mini, in: app)
        let close = app.buttons["laughtrack.now-playing.close"]
        XCTAssertEqual(close.value as? String, "Regular layout")
        XCTAssertTrue(element("laughtrack.now-playing.sleep", in: app).isHittable)
        attach(app, "iPad — expanded player")
        close.tap()
        XCTAssertTrue(close.waitForNonExistence(timeout: 5))
        XCTAssertTrue(mini.isHittable)
        // Explicitly switch applications: iPad XCTest can report stale foreground
        // state after a synthetic Home press even with SpringBoard on screen.
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.activate()
        defer { settings.terminate() }
        XCTAssertTrue(
            app.wait(for: .runningBackground, timeout: 5) || app.state == .runningBackgroundSuspended,
            "App must enter a background state; actual state: \(app.state.rawValue)"
        )
        app.activate()
        XCTAssertTrue(element("laughtrack.home.screen", in: app).exists)
        XCTAssertTrue(mini.isHittable)
        XCTAssertFalse(element("laughtrack.launch.loading-logo", in: app).exists)
        attach(app, "iPad — player dismissed and app resumed")
    }

    private func verifyPlayerAndModalContinuity(largeText: Bool = false) throws {
        let app = try launchApp(seedPlayer: true, largeText: largeText)
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()
        XCTAssertTrue(element("laughtrack.shows-search.screen", in: app).waitForExistence(timeout: 10))
        let miniPlayer = element("laughtrack.podcast-mini-player", in: app)
        XCTAssertTrue(miniPlayer.waitForExistence(timeout: 5))
        let originalFrame = miniPlayer.frame
        expandPlayer(miniPlayer, in: app)
        attach(app, "Native player sheet — expanded")
        if largeText {
            let sleep = element("laughtrack.now-playing.sleep", in: app)
            for _ in 0..<5 where !sleep.isHittable { app.swipeUp() }
            XCTAssertTrue(sleep.isHittable, "Lower playback controls must remain reachable at accessibility text sizes")
            XCTAssertTrue(app.buttons["laughtrack.now-playing.close"].isHittable, "Close remains visible while player content scrolls")
            attach(app, "Large text — lower player controls and fixed Close")
        }
        app.buttons["laughtrack.now-playing.close"].tap()
        assertSearchAndPlayer(app, originalFrame: originalFrame)
        attach(app, "Player — close button restored Search")

        expandPlayer(miniPlayer, in: app)
        let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.08))
        let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.85))
        start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.1)
        assertSearchAndPlayer(app, originalFrame: originalFrame)
        attach(app, "Player — native sheet swipe dismissed")

        let account = app.buttons["laughtrack.account.header-button"]
        XCTAssertTrue(account.isHittable)
        account.tap()
        let signIn = app.buttons["laughtrack.account.sign-up-button"]
        XCTAssertTrue(signIn.waitForExistence(timeout: 5))
        for _ in 0..<5 where !signIn.isHittable { app.swipeUp() }
        signIn.tap()
        let closeAuth = app.buttons["laughtrack.login.close"]
        XCTAssertTrue(closeAuth.waitForExistence(timeout: 5))
        XCTAssertTrue(closeAuth.isHittable, "Dismissal must remain reachable at large text")
        if largeText {
            let email = app.buttons["Email me a sign-in link"]
            for _ in 0..<6 where !email.isHittable { app.swipeUp() }
            XCTAssertTrue(email.isHittable, "Every sign-in option must remain reachable")
            XCTAssertTrue(closeAuth.isHittable)
        }
        attach(app, "Authentication — native sheet")
        closeAuth.tap()
        XCTAssertTrue(closeAuth.waitForNonExistence(timeout: 5))
        assertSearchAndPlayer(app, originalFrame: originalFrame)

        XCUIDevice.shared.press(.home)
        XCTAssertTrue(
            app.wait(for: .runningBackground, timeout: 5) || app.state == .runningBackgroundSuspended,
            "App must enter a background state; actual state: \(app.state.rawValue)"
        )
        app.activate()
        assertSearchAndPlayer(app, originalFrame: originalFrame)
        XCTAssertFalse(element("laughtrack.launch.loading-logo", in: app).exists)
        attach(app, "Search — background resume preserved player")

        let dragStart = miniPlayer.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.1))
        dragStart.press(forDuration: 0.05, thenDragTo: dragStart.withOffset(CGVector(dx: 0, dy: 20)), withVelocity: .slow, thenHoldForDuration: 0.1)
        assertSearchAndPlayer(app, originalFrame: originalFrame)
        attach(app, "Mini player — cancelled dismissal")
        dragStart.press(forDuration: 0.05, thenDragTo: dragStart.withOffset(CGVector(dx: 0, dy: 85)), withVelocity: .slow, thenHoldForDuration: 0.1)
        XCTAssertTrue(miniPlayer.waitForNonExistence(timeout: 5))
        XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
        attach(app, "Mini player — committed dismissal")
    }

    private func launchApp(seedPlayer: Bool = false, largeText: Bool = false) throws -> XCUIApplication {
        continueAfterFailure = false
        let port = ProcessInfo.processInfo.environment["LAUGHTRACK_SCREENSHOT_FIXTURE_PORT"] ?? "8765"
        let baseURL = "http://127.0.0.1:\(port)"
        let data = try Data(contentsOf: XCTUnwrap(URL(string: "\(baseURL)/fixture/configure?mode=curated")))
        let contract = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(contract["mode"] as? String, "curated")
        let app = XCUIApplication()
        app.launchArguments = [UITestLaunchArgs.resetState, UITestLaunchArgs.guestBrowsing, "-UITestMockMode"]
        if largeText {
            app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        }
        app.launchEnvironment["LAUGHTRACK_API_BASE_URL"] = baseURL
        if seedPlayer { app.launchEnvironment[UITestLaunchArgs.seedPodcastPlayer] = "1" }
        app.launch()
        XCTAssertTrue(app.buttons["Discover"].firstMatch.waitForExistence(timeout: 15))
        return app
    }

    private func expandPlayer(_ miniPlayer: XCUIElement, in app: XCUIApplication) {
        // Tap title artwork area, clear of the nested playback controls.
        miniPlayer.coordinate(withNormalizedOffset: CGVector(dx: 0.2, dy: 0.4)).tap()
        let close = app.buttons["laughtrack.now-playing.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 5))
        XCTAssertTrue(close.isHittable)
    }

    private func assertSearchAndPlayer(_ app: XCUIApplication, originalFrame: CGRect) {
        let close = app.buttons["laughtrack.now-playing.close"]
        XCTAssertTrue(close.waitForNonExistence(timeout: 5))
        XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
        let mini = element("laughtrack.podcast-mini-player", in: app)
        XCTAssertTrue(mini.isHittable)
        XCTAssertEqual(mini.frame.minY, originalFrame.minY, accuracy: 3)
        XCTAssertEqual(mini.frame.height, originalFrame.height, accuracy: 3)
        XCTAssertTrue(mini.staticTexts["Watch Your Tone with Ryan Sickler | History Hyenas"].exists, "Sheet dismissal must preserve the seeded episode")
    }

    private func edgeDrag(in app: XCUIApplication, to fraction: CGFloat) {
        let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.005, dy: 0.5))
        let end = app.coordinate(withNormalizedOffset: CGVector(dx: fraction, dy: 0.5))
        start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.3)
    }

    private func position(_ marker: XCUIElement, at targetY: CGFloat, in app: XCUIApplication) {
        for _ in 0..<5 {
            let distance = marker.frame.minY - targetY
            if abs(distance) < 8 { return }
            let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.7))
            let end = start.withOffset(CGVector(dx: 0, dy: -min(max(distance, -220), 320)))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.3)
        }
    }

    private func assertPosition(_ marker: XCUIElement, y: CGFloat) {
        XCTAssertTrue(marker.waitForExistence(timeout: 5))
        XCTAssertEqual(marker.frame.minY, y, accuracy: 3, "Returning must preserve the pixel offset, not just the section")
    }

    private func element(_ identifier: String, in app: XCUIApplication) -> XCUIElement {
        app.descendants(matching: .any)[identifier].firstMatch
    }

    private func attach(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
