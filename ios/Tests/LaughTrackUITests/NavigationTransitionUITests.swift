import Foundation
import XCTest
import UIKit

/// Real navigation, populated by scripts/screenshots/fixture_server.py. No mock
/// navigation root or forced full-screen player: only data and paused playback
/// are seeded. Run these cases at native default/large text and Reduce Motion.
@MainActor
final class NavigationTransitionUITests: XCTestCase {
    func testSearchEntityFavoritesKeepLoginAndDetailActionsSeparate() throws {
        let app = try launchApp()
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()

        let cases = [
            (category: "comedians", result: "laughtrack.comedians-search.result-301", title: "Ali Wong", detail: "laughtrack.comedian-detail.screen", hasFavorite: true),
            (category: "clubs", result: "laughtrack.clubs-search.result-201", title: "Hollywood Improv", detail: "laughtrack.club-detail.screen", hasFavorite: false),
            (category: "podcasts", result: "laughtrack.podcasts-search.result-podcast-401", title: "History Hyenas", detail: "laughtrack.podcast-detail-screen", hasFavorite: true),
        ]

        for item in cases {
            selectSearchCategory(item.category, in: app)
            let result = element(item.result, in: app)
            XCTAssertTrue(result.waitForExistence(timeout: 10))
            revealSearchResult(result, in: app)
            XCTAssertTrue(result.label.contains(item.title))
            XCTAssertGreaterThanOrEqual(result.frame.height, 44)
            attach(app, "Search \(item.category) — simplified entity rows")

            if item.hasFavorite {
                let favorite = app.buttons[item.result + ".favorite"]
                assertIndependentFavorite(favorite, beside: result, in: app)
                XCTAssertEqual(favorite.label, "Add \(item.title) to favorites")
                favorite.tap()
                let close = app.buttons["laughtrack.login.close"]
                XCTAssertTrue(close.waitForExistence(timeout: 5), "A guest favorite opens sign-in")
                XCTAssertFalse(element(item.detail, in: app).exists, "Favoriting must not also navigate")
                attach(app, "Search \(item.category) — favorite requests sign-in without opening detail")
                close.tap()
                XCTAssertTrue(close.waitForNonExistence(timeout: 5))
                XCTAssertTrue(result.isHittable)
                XCTAssertEqual(favorite.label, "Add \(item.title) to favorites", "Cancelling sign-in must not mark a favorite")
            }

            result.tap()
            XCTAssertTrue(element(item.detail, in: app).waitForExistence(timeout: 10))
            XCTAssertFalse(app.buttons["laughtrack.login.close"].exists, "Detail navigation must not trigger sign-in")
            edgeDrag(in: app, to: 0.88)
            XCTAssertTrue(result.waitForExistence(timeout: 5))
            XCTAssertTrue(app.tabBars.buttons["Search"].isSelected)
        }
    }

    func testAccessibilitySearchEntityRowsRetainLabelsAndSeparateTargets() throws {
        let app = try launchApp(largeText: true)
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()

        let cases = [
            (category: "comedians", result: "laughtrack.comedians-search.result-302", title: "Taylor Tomlinson", metadata: "", hasFavorite: true),
            (category: "clubs", result: "laughtrack.clubs-search.result-201", title: "Hollywood Improv", metadata: "Hollywood, CA", hasFavorite: false),
            (category: "podcasts", result: "laughtrack.podcasts-search.result-podcast-401", title: "History Hyenas", metadata: "Chris Distefano & Yannis Pappas", hasFavorite: true),
        ]

        for item in cases {
            selectSearchCategory(item.category, in: app)
            let result = element(item.result, in: app)
            XCTAssertTrue(result.waitForExistence(timeout: 10))
            revealSearchResult(result, in: app)
            let expectedLabel = item.metadata.isEmpty ? item.title : "\(item.title), \(item.metadata)"
            XCTAssertEqual(result.label, expectedLabel, "The accessible name must retain complete title and metadata")
            XCTAssertGreaterThanOrEqual(result.frame.height, 44)
            if item.hasFavorite {
                assertIndependentFavorite(app.buttons[item.result + ".favorite"], beside: result, in: app)
            }
            // Full accessibility labels alone cannot prove visually untruncated
            // text; retain a real rendered capture for title/metadata inspection.
            attach(app, "Accessibility Search \(item.category) — full name and independent row targets")
        }
    }

    private func selectSearchCategory(_ category: String, in app: XCUIApplication) {
        let button = app.buttons["laughtrack.primitive-filter.\(category)"]
        XCTAssertTrue(button.waitForExistence(timeout: 5))
        let window = app.windows.firstMatch.frame
        let leadingX = max(window.minX + 16, app.buttons["laughtrack.account.header-button"].frame.maxX + 8)
        // The category scroller's shipping trailing inset is eight points.
        let trailingX = window.maxX - 8
        for _ in 0..<8 {
            let frame = button.frame
            if button.isHittable && frame.minX >= leadingX - 1 && frame.maxX <= trailingX + 1 { break }
            // Center the requested category with a bounded drag. A full-width
            // left swipe can pass an intermediate category entirely; recompute
            // the signed distance so an overshoot is corrected to the right.
            let centerX = (leadingX + trailingX) / 2
            let distance = centerX - frame.midX
            let displacement = min(max(distance, -140), 140)
            let origin = app.coordinate(withNormalizedOffset: .zero)
            let start = origin.withOffset(CGVector(dx: centerX - app.frame.minX, dy: frame.midY - app.frame.minY))
            let end = start.withOffset(CGVector(dx: displacement, dy: 0))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        }
        assertCategoryFullyVisible(button, in: app)
        XCTAssertGreaterThanOrEqual(button.frame.minX, leadingX - 1, "The account control must not obscure the category")
        XCTAssertLessThanOrEqual(button.frame.maxX, trailingX + 1)
        button.tap()
        assertSelectedCategory(category, in: app)
    }

    private func revealSearchResult(_ result: XCUIElement, in app: XCUIApplication) {
        let window = app.windows.firstMatch.frame
        let selectedCategory = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND isSelected == true", "laughtrack.primitive-filter."
        )).firstMatch
        XCTAssertTrue(selectedCategory.exists)
        let top = selectedCategory.frame.maxY + 12
        let bottom = app.tabBars.firstMatch.frame.minY - 12
        let viewport = CGRect(x: window.minX, y: top, width: window.width, height: bottom - top)
        XCTAssertLessThanOrEqual(result.frame.height, viewport.height + 1,
                                 "Result cannot fit in its viewport: result=\(result.frame), viewport=\(viewport)")

        for _ in 0..<8 {
            let frame = result.frame
            if result.isHittable && frame.minY >= top - 1 && frame.maxY <= bottom + 1 { break }
            // Category changes retain the Search scroll position. A result can
            // be partially above the header as well as below the tab bar; use
            // signed, measured drags instead of always swiping upward.
            let displacement = min(max(viewport.midY - frame.midY, -180), 180)
            let origin = app.coordinate(withNormalizedOffset: .zero)
            let start = origin.withOffset(CGVector(dx: viewport.midX - app.frame.minX, dy: viewport.midY - app.frame.minY))
            let end = start.withOffset(CGVector(dx: 0, dy: displacement))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        }
        let diagnostic = "result=\(result.frame), viewport=\(viewport), window=\(window)"
        XCTAssertTrue(result.isHittable, diagnostic)
        XCTAssertTrue(window.insetBy(dx: -1, dy: -1).contains(result.frame), diagnostic)
        XCTAssertGreaterThanOrEqual(result.frame.minY, top - 1, "The complete result must clear the category header: \(diagnostic)")
        XCTAssertLessThanOrEqual(result.frame.maxY, bottom + 1, "The complete result must clear the tab bar: \(diagnostic)")
    }

    private func assertIndependentFavorite(_ favorite: XCUIElement, beside result: XCUIElement, in app: XCUIApplication) {
        XCTAssertTrue(favorite.waitForExistence(timeout: 5))
        XCTAssertTrue(favorite.isHittable)
        XCTAssertGreaterThanOrEqual(favorite.frame.width, 44)
        XCTAssertGreaterThanOrEqual(favorite.frame.height, 44)
        XCTAssertFalse(result.frame.intersects(favorite.frame), "Detail and favorite hit targets must not overlap")
        XCTAssertTrue(app.windows.firstMatch.frame.insetBy(dx: -1, dy: -1).contains(favorite.frame))
        XCTAssertLessThanOrEqual(favorite.frame.maxY, app.tabBars.firstMatch.frame.minY + 1)
    }

    func testSearchCategoriesFitAndAccountRemainsReachable() throws {
        let app = try launchApp()
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()

        let categories = ["shows", "comedians", "clubs", "podcasts"]
        for category in categories {
            let button = app.buttons["laughtrack.primitive-filter.\(category)"]
            XCTAssertTrue(button.waitForExistence(timeout: 5))
            assertCategoryFullyVisible(button, in: app)
            XCTAssertGreaterThanOrEqual(button.frame.width, 44)
            XCTAssertGreaterThanOrEqual(button.frame.height, 44)
        }
        assertSelectedCategory("shows", in: app)
        attach(app, "Search categories — all four visible without scrolling")

        for category in categories.dropFirst() {
            app.buttons["laughtrack.primitive-filter.\(category)"].tap()
            assertSelectedCategory(category, in: app)
        }

        let account = app.buttons["laughtrack.account.header-button"]
        XCTAssertTrue(account.isHittable)
        XCTAssertGreaterThanOrEqual(account.frame.width, 44)
        XCTAssertGreaterThanOrEqual(account.frame.height, 44)
        account.tap()
        let close = app.buttons["Close account drawer"]
        XCTAssertTrue(close.waitForExistence(timeout: 5))
        XCTAssertTrue(close.isHittable)
        XCTAssertTrue(app.buttons["laughtrack.account.sign-up-button"].exists)
        close.tap()
        XCTAssertTrue(close.waitForNonExistence(timeout: 5))
        assertSelectedCategory("podcasts", in: app)
        attach(app, "Search categories — account drawer dismissal retains selection")
    }

    func testAccessibilitySearchCategoryRevealsAndRestoresSelection() throws {
        let app = try launchApp(largeText: true)
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()
        let shows = app.buttons["laughtrack.primitive-filter.shows"]
        XCTAssertTrue(shows.waitForExistence(timeout: 5))
        assertSelectedCategory("shows", in: app)
        let headerY = shows.frame.midY
        let podcasts = app.buttons["laughtrack.primitive-filter.podcasts"]

        // Swipe only the category row, never the vertically scrolling results.
        // The row has no parent identifier that could overwrite its buttons.
        for _ in 0..<6 where !isCategoryFullyVisible(podcasts, in: app) {
            swipeCategoryHeader(in: app, y: headerY, towardTrailing: true)
        }
        assertCategoryFullyVisible(podcasts, in: app)
        podcasts.tap()
        assertSelectedCategory("podcasts", in: app)
        XCTAssertGreaterThanOrEqual(podcasts.frame.width, 44)
        XCTAssertGreaterThanOrEqual(podcasts.frame.height, 44)
        attach(app, "Accessibility Search — Podcasts selected and fully revealed")

        // Leave the selected category offscreen before changing destinations:
        // returning must reveal selection rather than retain this stale offset.
        for _ in 0..<6 where !isCategoryFullyVisible(shows, in: app) {
            swipeCategoryHeader(in: app, y: headerY, towardTrailing: false)
        }
        assertCategoryFullyVisible(shows, in: app)
        XCTAssertTrue(podcasts.isSelected)

        app.tabBars.buttons["Discover"].tap()
        XCTAssertTrue(app.tabBars.buttons["Discover"].isSelected)
        XCTAssertFalse(podcasts.exists, "Category navigation belongs only to Search")
        XCTAssertTrue(app.buttons["laughtrack.account.header-button"].isHittable)
        app.tabBars.buttons["Library"].tap()
        XCTAssertTrue(app.tabBars.buttons["Library"].isSelected)
        XCTAssertFalse(podcasts.exists)
        XCTAssertTrue(app.buttons["laughtrack.account.header-button"].isHittable)
        app.tabBars.buttons["Search"].tap()
        assertSelectedCategory("podcasts", in: app)
        attach(app, "Accessibility Search — selected category restored after Discover and Library")
    }

    func testSearchQueriesSurviveCategorySwitchesAndDetailReturn() throws {
        let app = try launchApp()
        defer { app.terminate() }
        app.tabBars.buttons["Search"].tap()
        let field = app.textFields["laughtrack.search.field"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText("Taylor")
        app.buttons["laughtrack.search.shows.club"].tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForNonExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "Club name")
        field.tap()
        field.typeText("Cellar")
        app.buttons["laughtrack.search.shows.comedian"].tap()
        XCTAssertEqual(field.value as? String, "Taylor")

        app.buttons["laughtrack.primitive-filter.comedians"].tap()
        XCTAssertEqual(field.value as? String, "Comedian name")
        field.tap()
        field.typeText("Taylor")
        app.keyboards.buttons["Search"].tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForNonExistence(timeout: 5))
        let result = element("laughtrack.comedians-search.result-301", in: app)
        XCTAssertTrue(result.waitForExistence(timeout: 10))
        result.tap()
        XCTAssertTrue(element("laughtrack.comedian-detail.screen", in: app).waitForExistence(timeout: 10))
        edgeDrag(in: app, to: 0.88)
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "Taylor")
        XCTAssertFalse(app.keyboards.firstMatch.exists)

        app.buttons["laughtrack.primitive-filter.clubs"].tap()
        XCTAssertEqual(field.value as? String, "Club name")
        field.tap()
        field.typeText("Stand")
        app.buttons["laughtrack.primitive-filter.podcasts"].tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForNonExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "Podcast title")
        field.tap()
        field.typeText("Comedy")
        app.buttons["laughtrack.search.field.clear"].tap()
        XCTAssertEqual(field.value as? String, "Podcast title")
        XCTAssertTrue(app.keyboards.firstMatch.exists, "Clearing keeps the input ready to type")
        app.buttons["laughtrack.primitive-filter.clubs"].tap()
        XCTAssertEqual(field.value as? String, "Stand")
        app.buttons["laughtrack.primitive-filter.comedians"].tap()
        XCTAssertEqual(field.value as? String, "Taylor")
        app.buttons["laughtrack.primitive-filter.shows"].tap()
        XCTAssertEqual(field.value as? String, "Taylor")
        app.buttons["laughtrack.search.shows.club"].tap()
        XCTAssertEqual(field.value as? String, "Cellar")
        attach(app, "Search — separate queries retained")
    }

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

    private func isCategoryFullyVisible(_ button: XCUIElement, in app: XCUIApplication) -> Bool {
        guard button.exists, button.isHittable else { return false }
        let visibleBounds = app.windows.firstMatch.frame.insetBy(dx: -1, dy: -1)
        return !button.frame.isEmpty && visibleBounds.contains(button.frame)
    }

    private func assertCategoryFullyVisible(
        _ button: XCUIElement,
        in app: XCUIApplication,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let revealed = XCTNSPredicateExpectation(
            predicate: NSPredicate { object, _ in
                guard let button = object as? XCUIElement, button.exists, button.isHittable else {
                    return false
                }
                return !button.frame.isEmpty &&
                    app.windows.firstMatch.frame.insetBy(dx: -1, dy: -1).contains(button.frame)
            },
            object: button
        )
        XCTAssertEqual(
            XCTWaiter.wait(for: [revealed], timeout: 5), .completed,
            "\(button.identifier) must be fully visible and hittable; frame: \(button.frame)",
            file: file, line: line
        )
    }

    private func assertSelectedCategory(
        _ category: String,
        in app: XCUIApplication,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let selected = app.buttons["laughtrack.primitive-filter.\(category)"]
        let selection = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "isSelected == true"), object: selected
        )
        XCTAssertEqual(XCTWaiter.wait(for: [selection], timeout: 5), .completed, file: file, line: line)
        assertCategoryFullyVisible(selected, in: app, file: file, line: line)
        for other in ["shows", "comedians", "clubs", "podcasts"] where other != category {
            XCTAssertFalse(
                app.buttons["laughtrack.primitive-filter.\(other)"].isSelected,
                "Only the active category should expose the selected trait", file: file, line: line
            )
        }
    }

    private func swipeCategoryHeader(in app: XCUIApplication, y: CGFloat, towardTrailing: Bool) {
        let window = app.windows.firstMatch.frame
        let account = app.buttons["laughtrack.account.header-button"]
        let leadingX = max(window.minX + 16, account.frame.maxX + 8)
        let trailingX = window.maxX - 16
        let origin = app.coordinate(withNormalizedOffset: .zero)
        let leading = origin.withOffset(CGVector(dx: leadingX - app.frame.minX, dy: y - app.frame.minY))
        let trailing = origin.withOffset(CGVector(dx: trailingX - app.frame.minX, dy: y - app.frame.minY))
        let start = towardTrailing ? trailing : leading
        let end = towardTrailing ? leading : trailing
        start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.1)
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
