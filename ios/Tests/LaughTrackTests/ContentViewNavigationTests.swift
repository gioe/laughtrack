import Foundation
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("ContentView navigation")
@MainActor
struct ContentViewNavigationTests {
    @Test("first launch waits for auth restoration before choosing a route")
    func firstLaunchWaitsForAuthRestoration() async throws {
        #expect(ContentView.rootSurface(
            authState: .restoring,
            hasLoadedCurrentUser: false,
            currentUser: nil
        ) == .loading)
        #expect(ContentView.rootSurface(
            authState: .signingIn(.apple),
            hasLoadedCurrentUser: false,
            currentUser: nil
        ) == .loading)
    }

    @Test("shell launch keeps splash visible until initial home load completes")
    func shellLaunchKeepsSplashVisibleUntilInitialHomeLoadCompletes() async throws {
        #expect(ContentView.shouldShowLaunchSplash(
            surface: .signedOutShell(message: nil),
            hasLoadedInitialHome: false,
            isHomeTabSelected: true
        ))
        #expect(ContentView.shouldShowLaunchSplash(
            surface: .authenticatedShell,
            hasLoadedInitialHome: false,
            isHomeTabSelected: true
        ))
        #expect(!ContentView.shouldShowLaunchSplash(
            surface: .signedOutShell(message: nil),
            hasLoadedInitialHome: true,
            isHomeTabSelected: true
        ))
        #expect(!ContentView.shouldShowLaunchSplash(
            surface: .signedOutShell(message: nil),
            hasLoadedInitialHome: false,
            isHomeTabSelected: false
        ))
        #expect(!ContentView.shouldShowLaunchSplash(
            surface: .loading,
            hasLoadedInitialHome: false,
            isHomeTabSelected: true
        ))
        #expect(!ContentView.shouldShowLaunchSplash(
            surface: .authChoiceGate(message: nil),
            hasLoadedInitialHome: false,
            isHomeTabSelected: true
        ))
    }

    @Test("signing in from the shell keeps the shell visible instead of flashing the splash")
    func signingInFromShellKeepsShellVisible() async throws {
        // A returning guest tapping a provider from Profile: the auth web sheet
        // presents over the shell, so the root surface must stay on the shell
        // rather than swapping to the loading splash.
        #expect(ContentView.rootSurface(
            authState: .signingIn(.google),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: true
        ) == .signedOutShell(message: nil))
    }

    @Test("first-launch signed-out user sees auth choice gate")
    func firstLaunchSignedOutUserSeesAuthChoiceGate() async throws {
        #expect(ContentView.rootSurface(
            authState: .signedOut(message: nil),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: false
        ) == .authChoiceGate(message: nil))
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])
    }

    @Test("choosing Continue as guest records choice and shows shell")
    func continueAsGuestRecordsChoiceAndShowsShell() async throws {
        let storage = AppStateStorage(
            userDefaults: UserDefaults(suiteName: "ContentViewNavigationTests.guest.\(UUID().uuidString)")!
        )
        let store = FirstEntryAuthChoiceStore(appStateStorage: storage)

        #expect(!store.hasResolvedFirstEntryChoice)

        store.continueAsGuest()

        #expect(store.hasResolvedFirstEntryChoice)
        #expect(FirstEntryAuthChoiceStore(appStateStorage: storage).hasResolvedFirstEntryChoice)
        #expect(ContentView.rootSurface(
            authState: .signedOut(message: nil),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: store.hasResolvedFirstEntryChoice
        ) == .signedOutShell(message: nil))
    }

    @Test("signing in resolves first entry so a later sign-out shows the shell, not the gate")
    func signingInResolvesFirstEntryChoice() async throws {
        // Regression: a user who signed in directly from the first-launch gate
        // (never tapped Continue as guest) must NOT be bounced back to the
        // full-screen FirstEntryAuthChoiceView on sign-out. ContentView marks the
        // choice resolved on the .authenticated transition; this exercises that the
        // store persists it and that rootSurface then keeps the shell.
        let storage = AppStateStorage(
            userDefaults: UserDefaults(suiteName: "ContentViewNavigationTests.signin.\(UUID().uuidString)")!
        )
        let store = FirstEntryAuthChoiceStore(appStateStorage: storage)

        #expect(!store.hasResolvedFirstEntryChoice)

        store.markSignedIn()

        #expect(store.hasResolvedFirstEntryChoice)
        // Persisted across store re-creation (i.e. survives an app relaunch).
        #expect(FirstEntryAuthChoiceStore(appStateStorage: storage).hasResolvedFirstEntryChoice)
        #expect(ContentView.rootSurface(
            authState: .signedOut(message: nil),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: store.hasResolvedFirstEntryChoice
        ) == .signedOutShell(message: nil))
    }

    @Test("returning guest bypasses auth choice gate")
    func returningGuestBypassesAuthChoiceGate() async throws {
        #expect(ContentView.rootSurface(
            authState: .signedOut(message: nil),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: true
        ) == .signedOutShell(message: nil))
    }

    @Test("returning guest keeps the shell visible and carries the signed-out message")
    func returningGuestKeepsShellVisible() async throws {
        let message = "Your session expired. Sign in again."

        #expect(ContentView.rootSurface(
            authState: .signedOut(message: message),
            hasLoadedCurrentUser: false,
            currentUser: nil,
            hasResolvedFirstEntryChoice: true
        ) == .signedOutShell(message: message))

        let presenter = LoginModalPresenter()
        #expect(!presenter.isPresented)
        presenter.present()
        #expect(presenter.isPresented)
        presenter.dismiss()
        #expect(!presenter.isPresented)
    }

    @Test("signed-out entry points route guests toward profile sign-in")
    func signedOutEntryPointsRouteGuestsTowardProfileSignIn() async throws {
        #expect(AppRoute.nearMeToolbarTarget(isSignedIn: false) == .profile)
        #expect(AppRoute.accountHeaderTarget() == .profile)
        #expect(ContentView.firstEntrySignedOutAuthOptions == ProfileView.signedOutAuthOptions)
    }

    @Test("first-entry auth options match profile options")
    func firstEntryAuthOptionsMatchProfileOptions() {
        #expect(ContentView.firstEntrySignedOutAuthOptions == ProfileView.signedOutAuthOptions)
        #expect(ContentView.firstEntrySignedOutAuthOptions == SignedOutAuthOption.all)
        #expect(ContentView.firstEntrySignedOutAuthOptions.map(\.provider) == [.apple, .google, .email])
    }

    @Test("first-entry auth option buttons have stable selectable identifiers")
    func firstEntryAuthOptionButtonsHaveStableSelectableIdentifiers() {
        #expect(LaughTrackViewTestID.firstEntryAuthOptionButton(.apple) == "laughtrack.auth-choice.option.apple")
        #expect(LaughTrackViewTestID.firstEntryAuthOptionButton(.google) == "laughtrack.auth-choice.option.google")
        #expect(LaughTrackViewTestID.firstEntryAuthOptionButton(.email) == "laughtrack.auth-choice.option.email")
    }

    @Test("content view routes authenticated users into the app shell")
    func contentViewRendersShell() async throws {
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])

        let shellState = AppShellState()
        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == nil)
        #expect(!shellState.showsLocationHeader)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [
            .showsTonight,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
    }

    @Test("home clubs pill keeps home focused on club backend content")
    func homeClubsPillKeepsHomeFocusedOnClubs() async throws {
        let shellState = AppShellState()

        shellState.selectPrimitive(.clubs)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .clubs)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [.clubs])
    }

    @Test("home shows pill keeps home focused on show backend content")
    func homeShowsPillKeepsHomeFocusedOnShows() async throws {
        let shellState = AppShellState()

        shellState.selectPrimitive(.shows)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .shows)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [
            .showsTonight,
            .thisWeek,
        ])
    }

    @Test("home comedians pill keeps home focused on comedian backend content")
    func homeComediansPillKeepsHomeFocusedOnComedians() async throws {
        let shellState = AppShellState()

        shellState.selectPrimitive(.comedians)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .comedians)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [.comedians])
    }

    @Test("location header stays hidden on the Discover tab when toggling primitive filters")
    func locationHeaderStaysHiddenOnDiscoverWhenTogglingPrimitives() async throws {
        let shellState = AppShellState()

        #expect(shellState.selectedTab == .nearMe)
        #expect(!shellState.showsLocationHeader)

        shellState.selectPrimitive(.clubs)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .clubs)
        #expect(!shellState.showsLocationHeader)
    }

    @Test("Profile entry point from near me pushes the expected navigation intent")
    func nearMeProfileButtonPushesProfileRoute() async throws {
        let coordinator = TypedNavigationCoordinator<AppRoute>()

        #expect(AppRoute.accountHeaderTarget() == .profile)
        #expect(AppRoute.nearMeToolbarTarget(isSignedIn: true) == .profile)
        #expect(AppRoute.nearMeToolbarTarget(isSignedIn: false) == .profile)

        coordinator.push(AppRoute.nearMeToolbarTarget(isSignedIn: true))
        let pushed = decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.profile])
    }

    @Test("ContentView switches between the near me and profile routes")
    func contentViewSwitchesBetweenRoutes() async throws {
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppRoute.profile.shellTab == nil)

        let coordinator = TypedNavigationCoordinator<AppRoute>()
        coordinator.push(AppRoute.profile)

        let pushed = decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.profile])
    }

    @Test("home shows-tonight hero is mounted with the show-detail accessibility id")
    func homeShowsTonightHeroIsMountedWithShowDetailAccessibilityId() async throws {
        #expect(HomeContentSection.sections(for: .shows).first == .showsTonight)
        #expect(EntityNavigationTarget.show(701).route == .showDetail(701))
    }

    @Test("home removes the search entry rail from the body")
    func homeRemovesSearchEntryRail() async throws {
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
        #expect(HomeContentSection.sections(for: .shows) == [
            .showsTonight,
            .thisWeek,
        ])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
    }

    @Test("ContentView renders the show detail route")
    func contentViewShowsShowDetailRoute() async throws {
        assertPushedRoutes([.showDetail(301)])
        #expect(AppRoute.showDetail(301).shellTab == nil)
    }

    @Test("ContentView renders the comedian detail route")
    func contentViewShowsComedianDetailRoute() async throws {
        assertPushedRoutes([.comedianDetail(101)])
        #expect(AppRoute.comedianDetail(101).shellTab == nil)
    }

    @Test("ContentView renders the club detail route")
    func contentViewShowsClubDetailRoute() async throws {
        assertPushedRoutes([.clubDetail(201)])
        #expect(AppRoute.clubDetail(201).shellTab == nil)
    }

    @Test("ContentView routes the shared search route through the shell tab")
    func contentViewShowsSearchShellRoute() async throws {
        let shellState = AppShellState()

        shellState.selectTab(try #require(AppRoute.search.shellTab))

        #expect(shellState.selectedTab == .search)
        #expect(shellState.resolvedSearchPrimitive == .shows)
        #expect(!shellState.showsLocationHeader)
    }

    @Test("ContentView routes the library route through the favorites shell tab")
    func contentViewShowsLibraryShellRoute() async throws {
        let shellState = AppShellState()

        shellState.selectTab(try #require(AppRoute.library.shellTab))

        #expect(shellState.selectedTab == .favorites)
        #expect(shellState.selectedPrimitive == nil)
        #expect(!shellState.showsLocationHeader)
    }

    @Test("Search shell route does not surface the Near Me location header button")
    func searchShellRouteHidesLocationHeaderButton() async throws {
        let shellState = AppShellState()

        shellState.selectTab(try #require(AppRoute.search.shellTab))

        #expect(shellState.selectedTab == .search)
        #expect(!shellState.showsLocationHeader)
    }

    @Test("Library shell route does not surface the Near Me location header button")
    func libraryShellRouteHidesLocationHeaderButton() async throws {
        let shellState = AppShellState()

        shellState.selectTab(try #require(AppRoute.library.shellTab))

        #expect(shellState.selectedTab == .favorites)
        #expect(!shellState.showsLocationHeader)
    }

    @Test("ContentView routes the profile route through the real profile surface")
    func contentViewShowsProfileShellRoute() async throws {
        assertPushedRoutes([.profile])
        #expect(AppRoute.profile.shellTab == nil)
    }

    @Test("detail chrome home action is absent at depth one and pops to root when deeper")
    func detailHomeActionGatedByStackDepth() throws {
        let coordinator = TypedNavigationCoordinator<AppRoute>()

        // Empty stack and depth one: back already returns to the root, so
        // the chrome must not offer a redundant home button.
        #expect(coordinator.detailHomeAction == nil)
        coordinator.open(.club(201))
        #expect(coordinator.detailHomeAction == nil)

        coordinator.open(.show(301))
        coordinator.open(.comedian(101))
        let homeAction = try #require(coordinator.detailHomeAction)

        homeAction()
        #expect(coordinator.routes.isEmpty)
    }

    private func assertPushedRoutes(_ routes: [AppRoute]) {
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        routes.forEach { coordinator.push($0) }
        #expect(decodedRoutes(in: coordinator, as: AppRoute.self) == routes)
    }
}
