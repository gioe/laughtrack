import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

#if canImport(UIKit)
@Suite("Search root")
@MainActor
struct SearchRootViewTests {
    @Test("search root shows compact query chrome and browse shortcuts")
    func searchRootShowsCompactChrome() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let favorites = ComedianFavoriteStore()
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "search-root-default")
        let host = HostedView(
            SearchRootView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: favorites,
                coordinator: coordinator,
                searchNavigationBridge: SearchNavigationBridge(),
                nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
            )
            .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Search nearby comedy")
        try host.requireText("Near Me")
        try host.requireText("Tonight")
        try host.requireText("Shows")
        try host.requireText("ZIP")
        try host.requireText("Use date range")
        try host.requireView(withIdentifier: LaughTrackViewTestID.showsSearchScreen)

        #expect(host.findText("Tune the search") == nil)
        #expect(host.findText("Keep location, sort, and dates in reach.") == nil)
        #expect(host.findText("Keep filters close and results dense.") == nil)
    }
}
#endif

@Suite("Search root model")
@MainActor
struct SearchRootModelTests {
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

    @Test("context summary reflects active shortcut framing")
    func contextSummaryReflectsShortcut() async throws {
        let model = SearchRootModel()

        #expect(model.contextSummary == "Nearby results first")

        model.selectShortcut("Tonight")
        #expect(model.contextSummary == "Local dates tonight")

        model.selectShortcut("This Week")
        #expect(model.contextSummary == "Local dates this week")
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
