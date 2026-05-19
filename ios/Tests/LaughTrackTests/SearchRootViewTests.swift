import Foundation
import SwiftUI
import Testing
import Combine
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Search root")
@MainActor
struct SearchRootViewTests {
    @Test("search root model keeps unified search state out of primitive model defaults")
    func searchRootModelUsesUnifiedSearchState() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            initialUseDateRange: false
        )
        let comediansModel = ComediansDiscoveryModel()
        let clubsModel = ClubsDiscoveryModel()
        let podcastsModel = PodcastSearchModel(fetcher: RecordingPodcastSearchFetcher())

        #expect(model.activePivot == .shows)
        #expect(model.query == "")
        #expect(model.selectedShortcut == "Near Me")
        #expect(SearchRootModel.Pivot.allCases == [.shows, .comedians, .clubs, .podcasts])
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Search shows")
        #expect(SearchRootModel.Pivot.podcasts.queryPrompt == "Search podcast titles")
        #expect(ShowDistanceOption.allCases.map(\.title) == ["10 mi", "25 mi", "50 mi", "100 mi"])
        #expect(!showsModel.dateRange.isActive)

        model.query = "Comedy Cellar"
        model.activePivot = .podcasts
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )

        #expect(podcastsModel.searchText == "Comedy Cellar")
        #expect(clubsModel.searchText == "")
        #expect(comediansModel.searchText == "")
        #expect(showsModel.comedianSearchText == "")
    }

    @Test("podcast search model requests podcast results")
    func podcastSearchModelRequestsPodcastResults() async throws {
        let fetcher = RecordingPodcastSearchFetcher(
            result: .success(.init(
                items: [
                    PodcastSearchResult(
                        id: "podcast-42",
                        title: "Comedy Bang Bang",
                        subtitle: "Earwolf",
                        href: "/podcast/comedy-bang-bang",
                        imageUrl: "https://example.com/cbb.jpg"
                    )
                ],
                total: 1
            ))
        )
        let model = PodcastSearchModel(fetcher: fetcher)

        model.searchText = "Comedy"
        await model.reload()

        #expect(fetcher.requests == [PodcastSearchRequest(query: "Comedy", limit: 20, sort: "show_count_desc")])
        guard case .success(let page) = model.phase else {
            Issue.record("Expected podcast search to load successfully")
            return
        }
        #expect(page.items.map(\.title) == ["Comedy Bang Bang"])
        #expect(page.total == 1)
    }

    @Test("podcast URLSession fetcher uses dedicated podcast search endpoint")
    func podcastURLSessionFetcherUsesDedicatedPodcastSearchEndpoint() async throws {
        let session = URLSession.stubbed(json: """
        {
            "data": [
                {
                    "id": 42,
                    "slug": "comedy-bang-bang",
                    "title": "Comedy Bang Bang",
                    "authorName": "Earwolf",
                    "websiteUrl": null,
                    "feedUrl": "https://example.com/feed.xml",
                    "imageUrl": "https://example.com/cbb.jpg",
                    "description": "A comedy podcast.",
                    "episodeCount": 12
                }
            ],
            "total": 1
        }
        """) { request in
            #expect(request.url?.path == "/api/v1/podcasts/search")
            let url = try #require(request.url)
            let components = try #require(URLComponents(url: url, resolvingAgainstBaseURL: false))
            #expect(components.queryItems?.first(where: { $0.name == "q" })?.value == "")
            #expect(components.queryItems?.first(where: { $0.name == "page" })?.value == "0")
            #expect(components.queryItems?.first(where: { $0.name == "size" })?.value == "20")
            #expect(components.queryItems?.first(where: { $0.name == "sort" })?.value == "popularity_desc")
            #expect(components.queryItems?.first(where: { $0.name == "type" }) == nil)
            #expect(components.queryItems?.first(where: { $0.name == "limit" }) == nil)
        }
        let fetcher = URLSessionPodcastSearchFetcher(
            baseURL: URL(string: "https://example.test")!,
            urlSession: session
        )

        let result = await fetcher.searchPodcasts(.init(query: "", limit: 20, sort: "popularity_desc"))

        guard case .success(let response) = result else {
            Issue.record("Expected podcast search fetcher to decode successfully")
            return
        }
        #expect(response.total == 1)
        #expect(response.items == [
            PodcastSearchResult(
                id: "podcast-42",
                title: "Comedy Bang Bang",
                subtitle: "Earwolf",
                href: "https://example.com/feed.xml",
                imageUrl: "https://example.com/cbb.jpg"
            )
        ])
    }

    @Test("podcast search results resolve to podcast detail navigation")
    func podcastSearchResultResolvesPodcastDetailNavigation() throws {
        let result = PodcastSearchResult(
            id: "podcast-42",
            title: "Comedy Bang Bang",
            subtitle: "Earwolf",
            href: "/podcast/comedy-bang-bang",
            imageUrl: nil
        )

        #expect(result.navigationTarget == .podcast(42))
        #expect(result.navigationTarget?.route == .podcastDetail(42))
    }

    @Test("shows search reload debounces typed root queries before issuing transport calls")
    func showsSearchReloadDebouncesTypedRootQuery() async throws {
        let transport = StubClientTransport.alwaysFails()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let model = SearchRootModel()
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            initialUseDateRange: false
        )

        model.query = "Atsuko"
        model.applyQuery(to: showsModel)
        let reloadTask = Task {
            await showsModel.reload(apiClient: apiClient)
        }

        try await Task.sleep(for: .milliseconds(100))
        #expect(transport.capturedRequests.isEmpty)

        await reloadTask.value

        let request = try #require(transport.capturedRequests.last)
        #expect(request.operationID == "searchShows")
        #expect(searchRootQueryValue("comedian", from: request.path) == "Atsuko")
    }

    #if canImport(UIKit)
    @Test("shows list compact mode hides full search and filter chrome")
    func showsListCompactModeHidesFullSearchAndFilterChrome() async throws {
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shows-list-compact-mode")
        let nearbyLocationController = container.resolve(NearbyLocationController.self)
        let model = ShowsListModel(nearbyLocationController: nearbyLocationController)
        let coordinator = NavigationCoordinator<AppRoute>()
        let host = HostedView(
            ShowsListView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                model: model,
                compactMode: true,
                isActive: false
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
        )

        let dump = host.dumpAccessibilityTree()
        #expect(!dump.contains("Comedian"))
        #expect(!dump.contains("Club"))
        #expect(!dump.contains("Sort Earliest"))
        #expect(!dump.contains("Filter results"))
        #expect(dump.contains("Today"))
    }
    #endif
}

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

        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs])

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

    @Test("shell state shows podcasts only on the search tab")
    func shellStateShowsPodcastsOnlyOnSearchTab() async throws {
        let state = AppShellState()

        #expect(state.selectedTab == .nearMe)
        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs])

        state.selectTab(.search)

        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs, .podcasts])
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

    @Test("shell state publishes search primitive before activating search tab")
    func shellStatePublishesSearchPrimitiveBeforeActivatingSearchTab() async throws {
        let state = AppShellState()
        var selectedPrimitiveWhenSearchPublished: SearchRootModel.Pivot?
        let cancellable = state.$selectedTab.sink { tab in
            guard tab == .search else { return }
            selectedPrimitiveWhenSearchPublished = state.selectedPrimitive
        }

        state.selectTab(.search)
        cancellable.cancel()

        #expect(selectedPrimitiveWhenSearchPublished == .shows)
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
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Search shows")
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
        let seed = SearchRootModel.Seed(
            pivot: .shows,
            query: "",
            shortcut: "Near Me",
            nearbyPreference: NearbyPreference(zipCode: "10012", source: .manual, distanceMiles: 50)
        )

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
        let showsModel = ShowsListModel(
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
        #expect(showsModel.dateRange.isActive)
        #expect(showsModel.dateRange.from == calendar.startOfDay(for: now))
        #expect(showsModel.dateRange.to == calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: now)))
    }

    @Test("shows discovery model can start with date filtering disabled for search root")
    func showsDiscoveryModelCanStartWithDateFilteringDisabledForSearchRoot() async throws {
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            initialUseDateRange: false
        )

        #expect(!showsModel.dateRange.isActive)
        #expect(showsModel.requestKey.fromString == nil)
        #expect(showsModel.requestKey.toString == nil)
    }

    @Test("shows discovery applies nearby preference from a search seed")
    func showsDiscoveryAppliesNearbyPreferenceFromSearchSeed() async throws {
        let showsModel = makeShowsListModel(
            name: "seed-nearby",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        let preference = NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 50,
            city: "New York",
            state: "NY"
        )

        showsModel.applySearchSeedNearbyPreference(preference)

        #expect(showsModel.activeNearbyPreference == preference)
        #expect(showsModel.zipCodeDraft == "10012")
        #expect(showsModel.requestKey.sanitizedZip == "10012")
        #expect(showsModel.requestKey.distance.rawValue == 50)
    }

    @Test("near me shortcut resolves current location when no nearby preference exists")
    func nearMeShortcutResolvesCurrentLocation() async throws {
        let model = SearchRootModel()
        let showsModel = makeShowsListModel(
            name: "near-me-resolves",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )

        let succeeded = await model.selectShortcut("Near Me", showsModel: showsModel)

        #expect(succeeded)
        #expect(model.activePivot == .shows)
        #expect(model.selectedShortcut == "Near Me")
        #expect(showsModel.activeNearbyPreference == NearbyPreference(zipCode: "10012", source: .geolocated, distanceMiles: 25))
    }

    @Test("shows search location changes stay local to the search model")
    func showsSearchLocationDoesNotRewriteSharedNearMeDefault() async throws {
        let suiteName = "SearchRootModelTests.local-search-location.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let store = NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults))
        store.setManualZip("94108", distanceMiles: 25)
        let controller = NearbyLocationController(
            store: store,
            resolver: MockSearchNearbyLocationResolver(result: .success("10012")),
            zipLocationResolver: StubZipLocationResolver()
        )
        let showsModel = ShowsListModel(nearbyLocationController: controller)

        showsModel.zipCodeDraft = "30309"
        showsModel.distance = .regional
        let appliedManualZip = showsModel.applyManualZip()

        #expect(appliedManualZip)
        #expect(showsModel.activeNearbyPreference == NearbyPreference(zipCode: "30309", source: .manual, distanceMiles: 50))
        #expect(store.preference == NearbyPreference(zipCode: "94108", source: .manual, distanceMiles: 25))

        let appliedCurrentLocation = await showsModel.useCurrentLocation()

        #expect(appliedCurrentLocation)
        #expect(showsModel.activeNearbyPreference == NearbyPreference(zipCode: "10012", source: .geolocated, distanceMiles: 50))
        #expect(store.preference == NearbyPreference(zipCode: "94108", source: .manual, distanceMiles: 25))
    }

    @Test("near me shortcut clears an already resolved nearby preference")
    func nearMeShortcutClearsResolvedLocation() async throws {
        let model = SearchRootModel()
        let showsModel = makeShowsListModel(
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
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        let clubsModel = ClubsDiscoveryModel()
        let comediansModel = ComediansDiscoveryModel()
        let podcastsModel = PodcastSearchModel(fetcher: RecordingPodcastSearchFetcher())

        model.query = "Comedy Cellar"
        model.activePivot = .clubs
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(podcastsModel.searchText == "")
        #expect(comediansModel.searchText == "")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Atsuko"
        model.activePivot = .comedians
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
        #expect(comediansModel.searchText == "Atsuko")
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(podcastsModel.searchText == "")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Mark Normand"
        model.activePivot = .shows
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
        #expect(showsModel.comedianSearchText == "Mark Normand")
        #expect(showsModel.clubSearchText == "")

        model.query = "WTF"
        model.activePivot = .podcasts
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
        #expect(podcastsModel.searchText == "WTF")
        #expect(showsModel.comedianSearchText == "Mark Normand")
    }

    @Test("shows root query maps to comedian search for now")
    func showsRootQueryMapsToComedianSearch() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsListModel(
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

    private func makeShowsListModel(
        name: String,
        resolver: any NearbyLocationResolving
    ) -> ShowsListModel {
        let suiteName = "SearchRootModelTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return ShowsListModel(
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

private func searchRootQueryValue(_ name: String, from path: String?) -> String? {
    guard let path, let components = URLComponents(string: "https://test.example.com\(path)") else { return nil }
    return components.queryItems?.first(where: { $0.name == name })?.value
}

@MainActor
private final class RecordingPodcastSearchFetcher: PodcastSearchFetching {
    private(set) var requests: [PodcastSearchRequest] = []
    var result: Result<PodcastSearchResponse, LoadFailure>

    init(result: Result<PodcastSearchResponse, LoadFailure> = .success(.init(items: [], total: 0))) {
        self.result = result
    }

    func searchPodcasts(_ request: PodcastSearchRequest) async -> Result<PodcastSearchResponse, LoadFailure> {
        requests.append(request)
        return result
    }
}

private extension URLSession {
    static func stubbed(
        json: String,
        requestAssertions: @escaping @Sendable (URLRequest) throws -> Void
    ) -> URLSession {
        StubURLProtocol.handler = { request in
            try requestAssertions(request)
            let url = try #require(request.url)
            let response = try #require(HTTPURLResponse(
                url: url,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            ))
            return (response, Data(json.utf8))
        }

        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return URLSession(configuration: configuration)
    }
}

private final class StubURLProtocol: URLProtocol {
    nonisolated(unsafe) static var handler: (@Sendable (URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard let handler = Self.handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
