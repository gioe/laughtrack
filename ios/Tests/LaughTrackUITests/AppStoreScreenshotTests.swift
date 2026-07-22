import SharedKitTesting
import XCTest

/// UI test that captures the complete comparison screenshot set in sequence.
///
/// Driven by fastlane's `snapshot` tool via the `screenshots` lane:
/// `bundle exec fastlane screenshots`
///
/// Inherits boilerplate from `BaseAppStoreScreenshotTests` (XCUIApplication
/// setup and the `-UITestMockMode` launch argument).
/// Mock mode seeds Hollywood (90028), while the screenshot lane's local fixture
/// backend pins every entity, count, date, narrative, and artwork response.
@MainActor
final class AppStoreScreenshotTests: BaseAppStoreScreenshotTests {
    private enum TargetedCaptureComplete: Error {
        case done
    }

    private var selectedScenarioIDs: [String]?

    private enum Identifier {
        static let primitiveFilterScroller = "laughtrack.primitive-filter.scroller"
        static let clubDetailScreen = "laughtrack.club-detail.screen"
        static let showDetailScreen = "laughtrack.show-detail.screen"
        static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
        static let podcastDetailScreen = "laughtrack.podcast-detail-screen"
    }

    override func prepareForSnapshot() {
        setupSnapshot(app)
        if let index = app.launchArguments.firstIndex(of: "-ScreenshotScenarios"),
           app.launchArguments.indices.contains(index + 1)
        {
            selectedScenarioIDs = app.launchArguments[index + 1].split(separator: ",").map(String.init)
        }
        let port = ProcessInfo.processInfo.environment["LAUGHTRACK_SCREENSHOT_FIXTURE_PORT"] ?? "8765"
        app.launchEnvironment["LAUGHTRACK_API_BASE_URL"] = "http://127.0.0.1:\(port)"
    }

    func testGenerateAllScreenshots() throws {
        do {
            try generateScreenshots()
        } catch TargetedCaptureComplete.done {
            return
        }
    }

    private func generateScreenshots() throws {
        try capture(
            "01_NearMe",
            screen: identified("laughtrack.home.screen", as: "Near Me screen"),
            content: [
                identified("laughtrack.home.shows-tonight-rail", as: "Tonight rail"),
                noLoadingLabels(["Loading shows", "Loading trending comedians", "Loading popular clubs", "Loading trending podcasts"]),
            ]
        )

        relaunch(route: "search:0")
        assertFirstResult(identifierPrefix: "laughtrack.shows-search.result-", description: "show")
        try captureSearch("02_SearchShows", resultIdentifierPrefix: "laughtrack.shows-search.result-", description: "show")

        // Filter pills sit at the top of the search header. Use identifiers
        // instead of coordinates so the flow survives pill-width changes.
        tapPrimitive("comedians")
        assertFirstResult(identifierPrefix: "laughtrack.comedians-search.result-", description: "comedian")
        try captureSearch("03_SearchComedians", resultIdentifierPrefix: "laughtrack.comedians-search.result-", description: "comedian")

        tapPrimitive("clubs")
        assertFirstResult(identifierPrefix: "laughtrack.clubs-search.result-", description: "club")
        try captureSearch("04_SearchClubs", resultIdentifierPrefix: "laughtrack.clubs-search.result-", description: "club")

        searchFor(
            "The Comedy Store",
            resultIdentifierPrefix: "laughtrack.clubs-search.result-"
        )
        tapFirstResult(
            identifierPrefix: "laughtrack.clubs-search.result-",
            detailIdentifier: Identifier.clubDetailScreen,
            description: "club"
        )
        try capture(
            "05_ClubDetail",
            screen: identified(Identifier.clubDetailScreen, as: "club detail screen"),
            content: [
                text("The Comedy Store", as: "club title"),
                prefixed("laughtrack.shows-search.result-", as: "upcoming show"),
                noLoadingLabels(["Loading", "Loading shows"]),
            ]
        )

        // Keep Show Detail tied to the same club fixture on both platforms.
        // ClubDetailView's pinned calendar reuses the shows-search row IDs.
        tapFirstResult(
            identifierPrefix: "laughtrack.shows-search.result-",
            detailIdentifier: Identifier.showDetailScreen,
            description: "show"
        )
        try capture(
            "06_ShowDetail",
            screen: identified(Identifier.showDetailScreen, as: "show detail screen"),
            content: [
                text("Taylor Tomlinson & Friends", as: "show title"),
                noLoadingLabels(["Loading"]),
            ]
        )

        // Restart before the remaining search-tab captures so the shared
        // search query is clear and the flow does not depend on back-stack
        // coordinates from the detail screens.
        relaunchOnSearchTab()

        // Switch to Comedians filter for the comedian detail.
        tapPrimitive("comedians")

        searchFor(
            "Ali Wong",
            resultIdentifierPrefix: "laughtrack.comedians-search.result-"
        )

        tapFirstResult(
            identifierPrefix: "laughtrack.comedians-search.result-",
            detailIdentifier: Identifier.comedianDetailScreen,
            description: "comedian"
        )
        try capture(
            "07_ComedianDetail",
            screen: identified(Identifier.comedianDetailScreen, as: "comedian detail screen"),
            content: [
                text("Ali Wong", as: "comedian title"),
                identified("laughtrack.comedian-detail.tab-picker", as: "comedian detail tabs"),
                prefixed("laughtrack.shows-search.result-", as: "upcoming comedian show"),
                noLoadingLabels(["Loading", "Loading shows"]),
            ]
        )

        // Restart again before the podcast captures; the comedian detail has
        // its own Shows/Podcasts segmented control, so coordinate taps there
        // are not the global Search tab pivots.
        relaunchOnSearchTab()

        // Switch to Podcasts. The helper scrolls the identified primitive
        // scroller only when the pill is offscreen on the phone profile.
        tapPrimitive("podcasts")
        assertFirstResult(identifierPrefix: "laughtrack.podcasts-search.result-", description: "podcast")
        try captureSearch("08_SearchPodcasts", resultIdentifierPrefix: "laughtrack.podcasts-search.result-", description: "podcast")

        searchFor(
            "The Joe Rogan Experience",
            resultIdentifierPrefix: "laughtrack.podcasts-search.result-"
        )
        tapFirstResult(
            identifierPrefix: "laughtrack.podcasts-search.result-",
            detailIdentifier: Identifier.podcastDetailScreen,
            description: "podcast"
        )
        try capture(
            "09_PodcastDetail",
            screen: identified(Identifier.podcastDetailScreen, as: "podcast detail screen"),
            content: [
                text("The Joe Rogan Experience", as: "podcast title"),
                noLoadingLabels(["Loading"]),
            ]
        )

        relaunch(route: "profile:0")
        assertExists("laughtrack.profile-tab.screen", message: "Expected Profile screen")
        for benefit in [
            "Sign in to sync favorite comedians across devices.",
            "Saved Near Me location",
            "Alert preferences",
        ] {
            XCTAssertTrue(
                app.staticTexts[benefit].waitForExistence(timeout: 10),
                "Expected guest profile benefit: \(benefit)"
            )
        }
        for option in ["Continue with Apple", "Continue with Google", "Email me a sign-in link"] {
            let button = app.buttons[option]
            XCTAssertTrue(button.waitForExistence(timeout: 10), "Expected auth option: \(option)")
            XCTAssertTrue(button.isHittable, "Expected visible auth option: \(option)")
        }
        try capture(
            "11_Profile",
            screen: identified("laughtrack.profile-tab.screen", as: "guest Profile screen"),
            content: [allButtons(["Continue with Apple", "Continue with Google", "Email me a sign-in link"], as: "guest sign-in options")]
        )

        relaunch(environment: [UITestLaunchArgs.forceComedianOnboardingScreen: "1"])
        assertExists("laughtrack.onboarding.screen", message: "Expected onboarding screen")
        try capture(
            "13_Onboarding",
            screen: identified("laughtrack.onboarding.screen", as: "onboarding screen"),
            content: [
                identified("laughtrack.onboarding.search-field", as: "onboarding search field"),
                noLoadingLabels(["Loading comedians", "Finding more comedians"]),
            ]
        )

        relaunch(comparisonScreens: true)
        let miniPlayer = element("laughtrack.podcast-mini-player")
        XCTAssertTrue(miniPlayer.waitForExistence(timeout: 10), "Expected seeded podcast mini player")
        miniPlayer.coordinate(withNormalizedOffset: CGVector(dx: 0.35, dy: 0.5)).tap()
        assertExists("laughtrack.now-playing-screen", message: "Expected Now Playing screen")
        // Intentional background override: this immersive media surface uses
        // an opaque semantic canvas instead of the inherited app atmosphere.
        try capture(
            "14_NowPlaying",
            screen: identified("laughtrack.now-playing-screen", as: "Now Playing screen"),
            content: [text("The LaughTrack Comedy Roundup", as: "seeded episode")]
        )

        relaunch(route: "favorites:0", authenticatedPersona: true)
        assertExists("laughtrack.favorites-tab.screen", message: "Expected authenticated Favorites screen")
        try capture(
            "15_AuthenticatedFavorites",
            screen: identified("laughtrack.favorites-tab.screen", as: "authenticated Favorites screen"),
            content: [text("Taylor Tomlinson Live", as: "saved favorite show")]
        )

        relaunch(route: "profile:0", authenticatedPersona: true)
        assertExists("laughtrack.profile-tab.screen", message: "Expected authenticated Profile screen")
        try capture(
            "16_AuthenticatedProfile",
            screen: identified("laughtrack.profile-tab.screen", as: "authenticated Profile screen"),
            content: [text("Jordan Rivera", as: "authenticated persona")]
        )

        relaunch(route: "notifications:0", authenticatedPersona: true)
        assertExists("laughtrack.notifications.screen", message: "Expected authenticated Notifications screen")
        try capture(
            "17_AuthenticatedNotifications",
            screen: identified("laughtrack.notifications.screen", as: "authenticated Notifications screen"),
            content: [text("Taylor Tomlinson has a show near you", as: "seeded notification")]
        )

        // Use the real production login sheet through a DEBUG-only launch
        // seam. Provider buttons remain untouched, so external OAuth is never
        // part of the deterministic comparison run.
        relaunch(
            route: "profile:0",
            environment: [UITestLaunchArgs.forceLoginPrompt: "1"]
        )
        XCTAssertTrue(
            app.staticTexts["Pick up where you left off"].waitForExistence(timeout: 10),
            "Expected in-app auth prompt"
        )
        for option in ["Continue with Apple", "Continue with Google", "Email me a sign-in link"] {
            XCTAssertTrue(app.buttons[option].exists, "Expected auth option: \(option)")
        }
        // Intentional background override: the focused authentication sheet
        // uses an opaque semantic canvas over the ordinary catalog surface.
        try capture(
            "18_AuthPrompt",
            screen: text("Pick up where you left off", as: "authentication prompt"),
            content: [allButtons(["Continue with Apple", "Continue with Google", "Email me a sign-in link"], as: "authentication options")]
        )

        // Mock mode normally records the guest choice so comparison captures can
        // enter the shell. Suppress that one seed and capture the real root gate.
        relaunch(environment: [UITestLaunchArgs.forceFirstEntryAuthChoice: "1"])
        assertExists(
            "laughtrack.auth-choice.screen",
            message: "Expected full-screen first-entry auth choice"
        )
        for option in ["Continue as guest", "Continue with Apple", "Continue with Google", "Email me a sign-in link"] {
            XCTAssertTrue(app.buttons[option].exists, "Expected first-entry option: \(option)")
        }
        // Intentional background override: the first-entry gate is a
        // specialized authentication experience with an opaque canvas.
        try capture(
            "19_FirstEntryAuthChoice",
            screen: identified("laughtrack.auth-choice.screen", as: "first-entry auth choice"),
            content: [allButtons(["Continue as guest", "Continue with Apple", "Continue with Google", "Email me a sign-in link"], as: "first-entry options")]
        )
    }

    private func tapPrimitive(_ primitive: String) {
        let button = app.buttons["laughtrack.primitive-filter.\(primitive)"]
        XCTAssertTrue(button.waitForExistence(timeout: 10), "Expected \(primitive) primitive filter")
        if !button.isHittable {
            let scroller = element(Identifier.primitiveFilterScroller)
            XCTAssertTrue(scroller.waitForExistence(timeout: 5), "Expected primitive filter scroller")
            for _ in 0..<3 where !button.isHittable {
                scroller.swipeLeft()
            }
        }
        XCTAssertTrue(button.isHittable, "Expected \(primitive) primitive filter to be hittable")
        button.tap()
    }

    private func searchFor(_ query: String, resultIdentifierPrefix: String) {
        let field = app.textFields["laughtrack.search.field"].firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 10), "Expected global search field")
        field.tap()
        field.typeText(query)
        assertFirstResult(identifierPrefix: resultIdentifierPrefix, description: query)
    }

    private func relaunchOnSearchTab() {
        relaunch(route: "search:0")
    }

    private func relaunch(
        route: String? = nil,
        comparisonScreens: Bool = false,
        authenticatedPersona: Bool = false,
        environment: [String: String] = [:]
    ) {
        app.terminate()
        app.launchEnvironment.removeValue(forKey: "LAUNCHTRACK_DEBUG_ROUTE")
        app.launchEnvironment.removeValue(forKey: UITestLaunchArgs.forceComparisonScreens)
        app.launchEnvironment.removeValue(forKey: UITestLaunchArgs.forceComedianOnboardingScreen)
        app.launchEnvironment.removeValue(forKey: UITestLaunchArgs.authenticatedScreenshotPersona)
        app.launchEnvironment.removeValue(forKey: UITestLaunchArgs.forceLoginPrompt)
        app.launchEnvironment.removeValue(forKey: UITestLaunchArgs.forceFirstEntryAuthChoice)
        if let route {
            app.launchEnvironment["LAUNCHTRACK_DEBUG_ROUTE"] = route
        }
        if comparisonScreens {
            app.launchEnvironment[UITestLaunchArgs.forceComparisonScreens] = "1"
        }
        if authenticatedPersona {
            app.launchEnvironment[UITestLaunchArgs.authenticatedScreenshotPersona] = "1"
        }
        environment.forEach { app.launchEnvironment[$0.key] = $0.value }
        app.launch()
    }

    private func captureSearch(
        _ name: String,
        resultIdentifierPrefix: String,
        description: String
    ) throws {
        try capture(
            name,
            screen: identified("laughtrack.search.field", as: "Search screen"),
            content: [
                prefixed(resultIdentifierPrefix, as: "loaded \(description) result"),
                noLoadingLabels(["Loading \(description)s"]),
            ]
        )
    }

    private func capture(
        _ name: String,
        screen: SnapshotReadinessCondition,
        content: [SnapshotReadinessCondition]
    ) throws {
        if let selectedScenarioIDs, !selectedScenarioIDs.contains(name) {
            return
        }
        let artwork = SnapshotReadinessCondition(
            description: "required artwork loaded (no visible activity indicators)"
        ) { [unowned self] in
            !self.app.activityIndicators.allElementsBoundByIndex.contains { indicator in
                indicator.exists && !indicator.frame.isEmpty && self.app.frame.intersects(indicator.frame)
            }
        }
        try snapshot(name, whenReady: [screen] + content + [artwork])
        if selectedScenarioIDs?.last == name {
            throw TargetedCaptureComplete.done
        }
    }

    private func identified(_ identifier: String, as description: String) -> SnapshotReadinessCondition {
        SnapshotReadinessCondition(description: "screen/content: \(description)") { [unowned self] in
            self.app.descendants(matching: .any)[identifier].exists
        }
    }

    private func prefixed(_ prefix: String, as description: String) -> SnapshotReadinessCondition {
        SnapshotReadinessCondition(description: "loaded content: \(description)") { [unowned self] in
            let predicate = NSPredicate(format: "identifier BEGINSWITH %@", prefix)
            return self.app.descendants(matching: .any).matching(predicate).firstMatch.exists
        }
    }

    private func text(_ value: String, as description: String) -> SnapshotReadinessCondition {
        SnapshotReadinessCondition(description: "loaded content: \(description)") { [unowned self] in
            self.app.staticTexts[value].exists
        }
    }

    private func allButtons(_ values: [String], as description: String) -> SnapshotReadinessCondition {
        SnapshotReadinessCondition(description: "loaded content: \(description)") { [unowned self] in
            values.allSatisfy { self.app.buttons[$0].exists }
        }
    }

    private func noLoadingLabels(_ labels: [String]) -> SnapshotReadinessCondition {
        SnapshotReadinessCondition(description: "loaded content: no loading placeholders (\(labels.joined(separator: ", ")))") { [unowned self] in
            labels.allSatisfy { !self.app.staticTexts[$0].exists }
        }
    }

    private func tapFirstResult(
        identifierPrefix: String,
        detailIdentifier: String,
        description: String
    ) {
        let result = firstResult(identifierPrefix: identifierPrefix)
        XCTAssertTrue(result.waitForExistence(timeout: 15), "Expected first \(description) result")
        for _ in 0..<3 where !result.isHittable {
            app.swipeUp()
        }
        XCTAssertTrue(result.isHittable, "Expected first \(description) result to be hittable")
        result.tap()
        assertExists(detailIdentifier, message: "Expected \(description) detail")
    }

    private func assertFirstResult(identifierPrefix: String, description: String) {
        XCTAssertTrue(
            firstResult(identifierPrefix: identifierPrefix).waitForExistence(timeout: 15),
            "Expected first \(description) result"
        )
    }

    private func firstResult(identifierPrefix: String) -> XCUIElement {
        let predicate = NSPredicate(format: "identifier BEGINSWITH %@", identifierPrefix)
        return app.descendants(matching: .any).matching(predicate).firstMatch
    }

    private func assertExists(_ identifier: String, message: String) {
        XCTAssertTrue(element(identifier).waitForExistence(timeout: 15), message)
    }

    private func element(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any)[identifier]
    }
}
