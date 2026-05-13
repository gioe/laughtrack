import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("ContentView navigation")
@MainActor
struct ContentViewNavigationTests {
    @Test("content view routes authenticated users into the app shell")
    func contentViewRendersShell() async throws {
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])

        let shellState = AppShellState()
        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == nil)
        #expect(shellState.showsLocationHeader)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [
            .shows,
            .favoriteShows,
            .comedians,
            .clubs,
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
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [.shows])
    }

    @Test("home comedians pill keeps home focused on comedian backend content")
    func homeComediansPillKeepsHomeFocusedOnComedians() async throws {
        let shellState = AppShellState()

        shellState.selectPrimitive(.comedians)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .comedians)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [.comedians])
    }

    @Test("location header button stays on the near me tab when toggling primitive filters")
    func locationHeaderButtonStaysOnNearMeWhenTogglingPrimitives() async throws {
        let shellState = AppShellState()

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.showsLocationHeader)

        shellState.selectPrimitive(.clubs)

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == .clubs)
        #expect(shellState.showsLocationHeader)
    }

    @Test("Profile entry point from near me pushes the expected navigation intent")
    func nearMeProfileButtonPushesProfileRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()

        #expect(AppRoute.accountHeaderTarget() == .profile)
        #expect(AppRoute.nearMeToolbarTarget(isSignedIn: true) == .profile)
        #expect(AppRoute.nearMeToolbarTarget(isSignedIn: false) == .profile)

        coordinator.path.append(AppRoute.nearMeToolbarTarget(isSignedIn: true))
        let pushed = try decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.profile])
    }

    @Test("ContentView switches between the near me and profile routes")
    func contentViewSwitchesBetweenRoutes() async throws {
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppRoute.profile.shellTab == nil)

        let coordinator = NavigationCoordinator<AppRoute>()
        coordinator.path.append(AppRoute.profile)

        let pushed = try decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.profile])
    }

    @Test("home shows-tonight hero is mounted with the show-detail accessibility id")
    func homeShowsTonightHeroIsMountedWithShowDetailAccessibilityId() async throws {
        #expect(HomeContentSection.sections(for: .shows) == [.shows])
        #expect(EntityNavigationTarget.show(701).route == .showDetail(701))
    }

    @Test("home removes the search entry rail from the body")
    func homeRemovesSearchEntryRail() async throws {
        #expect(HomeContentSection.sections(for: nil) == [.shows, .favoriteShows, .comedians, .clubs])
        #expect(HomeContentSection.sections(for: .shows) == [.shows])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
    }

    @Test("ContentView renders the show detail route")
    func contentViewShowsShowDetailRoute() async throws {
        try assertPushedRoutes([.showDetail(301)])
        #expect(AppRoute.showDetail(301).shellTab == nil)
    }

    @Test("ContentView renders the comedian detail route")
    func contentViewShowsComedianDetailRoute() async throws {
        try assertPushedRoutes([.comedianDetail(101)])
        #expect(AppRoute.comedianDetail(101).shellTab == nil)
    }

    @Test("ContentView renders the club detail route")
    func contentViewShowsClubDetailRoute() async throws {
        try assertPushedRoutes([.clubDetail(201)])
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
        try assertPushedRoutes([.profile])
        #expect(AppRoute.profile.shellTab == nil)
    }

    private func assertPushedRoutes(_ routes: [AppRoute]) throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        routes.forEach { coordinator.path.append($0) }
        #expect(try decodedRoutes(in: coordinator, as: AppRoute.self) == routes)
    }
}
