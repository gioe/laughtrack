import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

#if canImport(UIKit)
@Suite("Search root")
@MainActor
struct SearchRootViewTests {
    @Test("search root uses one search field and keeps primitive filters out of the content card")
    func searchRootOmitsMarketingHeader() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let favorites = ComedianFavoriteStore()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "search-root-default")
        let store = container.resolve(NearbyPreferenceStore.self)
        let host = HostedView(
            SearchRootView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: favorites,
                coordinator: coordinator,
                searchNavigationBridge: SearchNavigationBridge(),
                nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
        )

        #expect(host.findText("Start with nearby shows, then pivot into clubs or comedian profiles without leaving Search.") == nil)
        try host.requireView(withIdentifier: LaughTrackViewTestID.searchHeader)
        try host.requireText("Search")
        try host.requireText("Shows")
        try host.requireText("ZIP")
        try host.requireText("Use date range")
        try host.requireView(withIdentifier: LaughTrackViewTestID.showsSearchScreen)
        #expect(host.findText("Near Me") == nil)
        #expect(host.findText("Tonight") == nil)
        #expect(host.findText("This Week") == nil)

        #expect(host.findText("Tune the search") == nil)
        #expect(host.findText("Keep location, sort, and dates in reach.") == nil)
        #expect(host.findText("Keep filters close and results dense.") == nil)
    }
}
#endif

@Suite("Search root model")
@MainActor
struct SearchRootModelTests {
    @Test("shell state allows no selected primitive on the near me tab")
    func shellStateAllowsNoPrimitiveOnNearMe() async throws {
        let state = AppShellState()

        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == nil)
    }

    @Test("shell state restores the cached search primitive when search is selected")
    func shellStateRestoresCachedSearchPrimitive() async throws {
        let state = AppShellState()

        state.selectTab(.search)
        state.setSearchPrimitive(.clubs)
        #expect(state.selectedTab == .search)
        #expect(state.selectedPrimitive == .clubs)

        state.selectTab(.nearMe)
        #expect(state.selectedPrimitive == nil)

        state.selectTab(.search)
        #expect(state.selectedPrimitive == .clubs)
    }

    @Test("shell state keeps all primitives on the near me tab")
    func shellStateKeepsHomePrimitivesOnNearMe() async throws {
        let state = AppShellState()

        state.selectPrimitive(.shows)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .shows)

        state.selectPrimitive(.comedians)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .comedians)

        state.selectPrimitive(.clubs)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .clubs)
    }

    @Test("shell state keeps primitive filters on the favorites tab")
    func shellStateKeepsPrimitiveFiltersOnFavorites() async throws {
        let state = AppShellState()

        state.selectTab(.favorites)
        state.selectPrimitive(.shows)
        #expect(state.selectedTab == .favorites)
        #expect(state.selectedPrimitive == .shows)

        state.selectPrimitive(.shows)
        #expect(state.selectedTab == .favorites)
        #expect(state.selectedPrimitive == nil)
    }

    @Test("shell state toggles a repeated home primitive back to all content")
    func shellStateTogglesRepeatedHomePrimitiveToAllContent() async throws {
        let state = AppShellState()

        state.selectPrimitive(.clubs)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .clubs)

        state.selectPrimitive(.clubs)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == nil)
    }

    @Test("home primitive filters do not replace the cached search primitive")
    func homePrimitiveFiltersDoNotReplaceCachedSearchPrimitive() async throws {
        let state = AppShellState()

        state.selectTab(.search)
        state.setSearchPrimitive(.comedians)
        state.selectTab(.nearMe)

        state.selectPrimitive(.clubs)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .clubs)

        state.selectPrimitive(.clubs)
        #expect(state.selectedPrimitive == nil)

        state.selectTab(.search)
        #expect(state.selectedPrimitive == .comedians)
    }

    @Test("location header shows pitch until nearby is configured or manual ZIP is chosen")
    func locationHeaderShowsPitchUntilNearbyIsConfiguredOrManualZipIsChosen() async throws {
        let state = AppShellState()

        #expect(state.selectLocationHeader(hasNearbyPreference: false) == .presentPermissionPitch)
        #expect(state.isLocationPermissionPitchPresented)

        state.dismissLocationPermissionPitchForManualZip()
        #expect(!state.isLocationPermissionPitchPresented)
        #expect(state.selectLocationHeader(hasNearbyPreference: false) == .openSettings)
    }

    @Test("location header opens settings when nearby is already configured")
    func locationHeaderOpensSettingsWhenNearbyIsConfigured() async throws {
        let state = AppShellState()

        #expect(state.selectLocationHeader(hasNearbyPreference: true) == .openSettings)
        #expect(!state.isLocationPermissionPitchPresented)
    }

    @Test("shell state defaults search to shows when no primitive has been cached")
    func shellStateDefaultsSearchToShows() async throws {
        let state = AppShellState()

        state.selectTab(.search)

        #expect(state.selectedPrimitive == .shows)
    }

    @Test("switching pivots does not navigate away from search root")
    func switchingPivotsStaysInPlace() async throws {
        let model = SearchRootModel()
        #expect(model.activePivot == .shows)
        model.activePivot = .clubs
        #expect(model.activePivot == .clubs)
    }

    @Test("search model exposes compact prompt copy")
    func searchModelExposesCompactPromptCopy() async throws {
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Search nearby comedy")
        #expect(SearchRootModel.Pivot.shows.queryHelpText == "Start with nearby shows, then pivot into clubs or comedian profiles without leaving Search.")
    }

    @Test("search seeds update pivot query and shortcut")
    func searchSeedsUpdatePivotQueryAndShortcut() async throws {
        let model = SearchRootModel()

        model.applySeed(.init(pivot: .clubs, query: "Cellar", shortcut: "Tonight"))

        #expect(model.activePivot == .clubs)
        #expect(model.query == "Cellar")
        #expect(model.selectedShortcut == "Tonight")
    }

    @Test("home search bridge stores latest seed request")
    func homeSearchBridgeStoresLatestSeedRequest() async throws {
        let bridge = SearchNavigationBridge()
        let seed = SearchRootModel.Seed(pivot: .comedians, query: "Atsuko", shortcut: nil)

        bridge.openSearch(seed)

        #expect(bridge.request?.seed == seed)
    }

    @Test("home search bridge consumes seed requests once")
    func homeSearchBridgeConsumesSeedRequestsOnce() async throws {
        let bridge = SearchNavigationBridge()
        bridge.openSearch(.init(pivot: .shows, query: "", shortcut: "Near Me"))

        let request = try #require(bridge.request)
        bridge.clearRequest(request)

        #expect(bridge.request == nil)
    }

    @Test("shortcut selection applies show date filters")
    func shortcutSelectionAppliesShowDateFilters() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        let now = Date(timeIntervalSince1970: 1_710_000_000)
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!

        model.selectShortcut("Tonight")
        model.applyShortcutFilters(to: showsModel, now: now, calendar: calendar)

        #expect(model.activePivot == .shows)
        #expect(showsModel.useDateRange)
        #expect(showsModel.fromDate == calendar.startOfDay(for: now))
        #expect(showsModel.toDate == calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: now)))
    }

    @Test("near me shortcut resolves current location when no nearby preference exists")
    func nearMeShortcutResolvesCurrentLocation() async throws {
        let model = SearchRootModel()
        let showsModel = makeShowsDiscoveryModel(
            name: "near-me-resolves",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )

        let succeeded = await model.selectShortcut("Near Me", showsModel: showsModel)

        #expect(succeeded)
        #expect(model.activePivot == .shows)
        #expect(model.selectedShortcut == "Near Me")
        #expect(showsModel.activeNearbyPreference == NearbyPreference(zipCode: "10012", source: .geolocated, distanceMiles: 25))
    }

    @Test("near me shortcut clears an already resolved nearby preference")
    func nearMeShortcutClearsResolvedLocation() async throws {
        let model = SearchRootModel()
        let showsModel = makeShowsDiscoveryModel(
            name: "near-me-clears",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        showsModel.zipCodeDraft = "30309"
        _ = showsModel.applyManualZip()

        let succeeded = await model.selectShortcut("Near Me", showsModel: showsModel)

        #expect(succeeded)
        #expect(model.activePivot == .shows)
        #expect(model.selectedShortcut == nil)
        #expect(showsModel.activeNearbyPreference == nil)
    }

    @Test("root query is applied only to the active pivot model")
    func rootQueryAppliesToActivePivotModel() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        let clubsModel = ClubsDiscoveryModel()
        let comediansModel = ComediansDiscoveryModel()

        model.query = "Comedy Cellar"
        model.activePivot = .clubs
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(comediansModel.searchText == "")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Atsuko"
        model.activePivot = .comedians
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(comediansModel.searchText == "Atsuko")
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Mark Normand"
        model.activePivot = .shows
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(showsModel.comedianSearchText == "Mark Normand")
        #expect(showsModel.clubSearchText == "")
    }

    @Test("shows root query maps to comedian search for now")
    func showsRootQueryMapsToComedianSearch() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )

        showsModel.clubSearchText = "Comedy Cellar"
        model.query = "Mark Normand"
        model.applyQuery(to: showsModel)

        #expect(showsModel.comedianSearchText == "Mark Normand")
        #expect(showsModel.clubSearchText == "")
    }

    private func makeShowsDiscoveryModel(
        name: String,
        resolver: any NearbyLocationResolving
    ) -> ShowsDiscoveryModel {
        let suiteName = "SearchRootModelTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return ShowsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults)),
                resolver: resolver,
                zipLocationResolver: StubZipLocationResolver()
            )
        )
    }
}

@MainActor
private final class MockSearchNearbyLocationResolver: NearbyLocationResolving {
    let result: Result<String, Error>

    init(result: Result<String, Error>) {
        self.result = result
    }

    func requestCurrentZip() async throws -> String {
        try result.get()
    }
}
