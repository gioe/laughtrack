import Foundation
import SwiftUI
import Testing
import Combine
import HTTPTypes
import OpenAPIRuntime
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Search root")
@MainActor
struct SearchRootViewTests {
    @Test("shows pivot omits the global text field and mounts explicit show constraints")
    func showsPivotOmitsGlobalTextField() throws {
        let source = try String(contentsOf: searchRootViewSourceURL(), encoding: .utf8)

        #expect(source.contains("if model.activePivot != .shows"))
        let showsStart = try #require(source.range(of: "case .shows:\n            ShowsListView("))
        let comediansStart = try #require(source[showsStart.upperBound...].range(of: "case .comedians:"))
        let showsBlock = source[showsStart.lowerBound..<comediansStart.lowerBound]
        #expect(!showsBlock.contains("unifiedSearchText"))
        #expect(!showsBlock.contains("unifiedSearchPrompt"))
        #expect(source.contains("showsModel.applySearchSeed(request.seed.showSearch ?? ShowSearchSeed())"))
    }

    @Test("search results select list and grid compositions from width class")
    func searchResultsSelectAdaptiveComposition() {
        #expect(SearchResultsComposition.resolve(horizontalSizeClass: .compact) == .compactList)
        #expect(SearchResultsComposition.resolve(horizontalSizeClass: .regular) == .regularGrid)
        #expect(SearchResultsComposition.resolve(horizontalSizeClass: nil) == .compactList)
    }

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
        let clubsModel = makeSearchClubsDiscoveryModel()
        let podcastsModel = PodcastSearchModel(fetcher: RecordingPodcastSearchFetcher())

        #expect(model.activePivot == .shows)
        #expect(model.query == "")
        #expect(model.selectedShortcut == "Near Me")
        #expect(SearchRootModel.Pivot.allCases == [.shows, .comedians, .clubs, .podcasts])
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Filter shows")
        #expect(SearchRootModel.Pivot.podcasts.queryPrompt == "Search podcast titles")
        #expect(ShowDistanceOption.allCases.map(\.title) == ["10 mi", "25 mi", "50 mi", "100 mi"])
        #expect(ShowSortOption.allCases.map(\.title) == ["Earliest", "Latest", "Low price", "High price"])
        #expect(!ShowSortOption.allCases.map(\.rawValue).contains("popularity_desc"))
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
        model.includeEmpty = true
        await model.reload()

        #expect(fetcher.requests == [PodcastSearchRequest(query: "Comedy", limit: 20, sort: "show_count_desc", includeEmpty: true)])
        guard case .success(let page) = model.phase else {
            Issue.record("Expected podcast search to load successfully")
            return
        }
        #expect(page.items.map(\.title) == ["Comedy Bang Bang"])
        #expect(page.total == 1)
    }

    @Test("podcast generated-client fetcher uses dedicated podcast search endpoint")
    func podcastGeneratedFetcherUsesDedicatedPodcastSearchEndpoint() async throws {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            var response = HTTPResponse(status: .ok)
            response.headerFields[.contentType] = "application/json"
            return (response, HTTPBody("""
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
                        "episodeCount": 12,
                        "hosts": []
                    }
                ],
                "total": 1,
                "filters": []
            }
            """))
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.test")!,
            transport: transport,
            middlewares: [APIVersionPathMiddleware()]
        )
        let fetcher = APIPodcastSearchFetcher(apiClient: apiClient)

        let result = await fetcher.searchPodcasts(.init(query: "", limit: 20, sort: "popularity_desc", includeEmpty: true))

        let captured = try #require(transport.capturedRequests.first)
        #expect(captured.operationID == "searchPodcasts")
        #expect(captured.method == .get)
        let path = try #require(captured.path)
        let components = try #require(URLComponents(string: "https://example.test\(path)"))
        #expect(components.path == "/api/v1/podcasts/search")
        #expect(components.queryItems?.first(where: { $0.name == "q" })?.value == "")
        #expect(components.queryItems?.first(where: { $0.name == "page" })?.value == "0")
        #expect(components.queryItems?.first(where: { $0.name == "size" })?.value == "20")
        #expect(components.queryItems?.first(where: { $0.name == "sort" })?.value == "popularity_desc")
        #expect(components.queryItems?.first(where: { $0.name == "includeEmpty" })?.value == "true")
        #expect(components.queryItems?.first(where: { $0.name == "type" }) == nil)
        #expect(components.queryItems?.first(where: { $0.name == "limit" }) == nil)

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

    @Test("Podcast generated-client fetcher uses shared failure classification")
    func podcastGeneratedFetcherUsesSharedFailureClassification() async throws {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            (
                HTTPResponse(status: .tooManyRequests, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"Custom rate-limit copy"}"#)
            )
        }
        let apiClient = Client(
            serverURL: URL(string: "https://example.test")!,
            transport: transport,
            middlewares: [APIVersionPathMiddleware()]
        )
        let fetcher = APIPodcastSearchFetcher(apiClient: apiClient)

        let result = await fetcher.searchPodcasts(.init(query: "", limit: 20, sort: "popularity_desc", includeEmpty: true))

        guard case .failure(let failure) = result else {
            Issue.record("Expected podcast search fetcher to classify rate-limit failure")
            return
        }
        #expect(failure.message == "LaughTrack is rate-limiting podcasts right now. Please try again in a moment. (HTTP 429)")
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

    @Test("shows search sends explicit entity, format, and maximum-price constraints")
    func showsSearchSendsExplicitConstraints() async throws {
        let transport = StubClientTransport.alwaysFails()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            initialUseDateRange: false
        )

        showsModel.comedianSearchText = "Atsuko"
        showsModel.clubSearchText = "The Stand"
        showsModel.selectedFilterSlugs = ["improv"]
        showsModel.maximumPrice = .forty
        let reloadTask = Task {
            await showsModel.reload(apiClient: apiClient)
        }

        try await Task.sleep(for: .milliseconds(100))
        #expect(transport.capturedRequests.isEmpty)

        await reloadTask.value

        let request = try #require(transport.capturedRequests.last)
        #expect(request.operationID == "searchShows")
        #expect(searchRootQueryValue("comedian", from: request.path) == "Atsuko")
        #expect(searchRootQueryValue("club", from: request.path) == "The Stand")
        #expect(searchRootQueryValue("filters", from: request.path) == "improv")
        #expect(searchRootQueryValue("maxPrice", from: request.path) == "40.0")
    }

    @Test("shows list compact mode hides full search and filter chrome")
    func showsListCompactModeHidesFullSearchAndFilterChrome() async throws {
        // HostedView accessibility-tree wiring is broken on iOS 26.x / 18.6, so
        // the chrome can't be asserted via dumpAccessibilityTree (TASK-2535).
        // Compact vs. full chrome is now derived by the pure
        // ShowsListChromeVisibility that both ShowsListView and ShowFiltersPanel
        // consume, so verify that derivation directly.
        let compact = ShowsListChromeVisibility(compactMode: true)
        #expect(!compact.showsSearchFields)   // hides the Comedian/Club search fields
        #expect(!compact.showsSortControl)    // hides the "Sort Earliest" pill
        #expect(!compact.showsFilterControl)  // hides the "Filter results" pill
        #expect(compact.showsDateControl)     // keeps the date ("Today") pill

        let full = ShowsListChromeVisibility(compactMode: false)
        #expect(full.showsSearchFields)
        #expect(full.showsSortControl)
        #expect(full.showsFilterControl)
        #expect(full.showsDateControl)

        let unifiedRootChild = ShowsListChromeVisibility(compactMode: false, displaysSearchFields: false)
        #expect(!unifiedRootChild.showsSearchFields)
        #expect(unifiedRootChild.showsSortControl)
        #expect(unifiedRootChild.showsFilterControl)
        #expect(unifiedRootChild.showsDateControl)

        // The date control stays visible in compact mode and reflects the
        // default active "Today" range that the date pill renders.
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        #expect(model.dateRange.isActive)
    }

    private func searchRootViewSourceURL(filePath: String = #filePath) -> URL {
        URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Sources/LaughTrackApp/SearchRootView.swift")
    }
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

    @Test("shell state surfaces all primitives on the Discover tab")
    func shellStateKeepsHomePrimitivesOnNearMe() async throws {
        let state = AppShellState()

        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs, .podcasts])

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

    @Test("shell state surfaces podcasts on Discover and Search, hides it on Favorites")
    func shellStateSurfacesPodcastsOnDiscoverAndSearch() async throws {
        let state = AppShellState()

        #expect(state.selectedTab == .nearMe)
        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs, .podcasts])

        state.selectTab(.search)
        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs, .podcasts])

        state.selectTab(.favorites)
        #expect(state.visiblePrimitiveFilters == [.shows, .comedians, .clubs])
    }

    @Test("selectPrimitive(.podcasts) on Discover stays on Discover and surfaces the podcasts rail")
    func selectingPodcastsOnDiscoverStaysOnDiscover() async throws {
        let state = AppShellState()

        #expect(state.selectedTab == .nearMe)

        state.selectPrimitive(.podcasts)

        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == .podcasts)

        state.selectPrimitive(.podcasts)
        #expect(state.selectedTab == .nearMe)
        #expect(state.selectedPrimitive == nil)
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
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Filter shows")
        #expect(SearchRootModel.Pivot.shows.queryHelpText == "Browse by date, place, price, format, comedian, or club.")
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

    @Test("Discover entity seeds preserve only applicable constraints")
    func discoverEntitySeedsPreserveOnlyApplicableConstraints() {
        let nearby = NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 50
        )

        let comedians = SearchRootModel.Seed.discoverEntity(
            .comedians,
            nearbyPreference: nearby
        )
        let clubs = SearchRootModel.Seed.discoverEntity(
            .clubs,
            nearbyPreference: nearby
        )
        let podcasts = SearchRootModel.Seed.discoverEntity(
            .podcasts,
            nearbyPreference: nearby
        )

        #expect(comedians == .init(pivot: .comedians, query: "", shortcut: nil))
        #expect(clubs == .init(
            pivot: .clubs,
            query: "",
            shortcut: nil,
            nearbyPreference: nearby
        ))
        #expect(podcasts == .init(pivot: .podcasts, query: "", shortcut: nil))
    }

    @Test("home search bridge consumes seed requests once")
    func homeSearchBridgeConsumesSeedRequestsOnce() async throws {
        let bridge = SearchNavigationBridge()
        bridge.openSearch(.init(pivot: .shows, query: "", shortcut: "Near Me"))

        let request = try #require(bridge.request)
        bridge.clearRequest(request)

        #expect(bridge.request == nil)
    }

    @Test("shortcut seed applies show date filters")
    func shortcutSeedAppliesShowDateFilters() async throws {
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

        model.applySeed(.init(pivot: .shows, query: "", shortcut: "Tonight"))
        model.applyShortcutFilters(to: showsModel, now: now, calendar: calendar)

        #expect(model.activePivot == .shows)
        #expect(showsModel.dateRange.isActive)
        #expect(showsModel.dateRange.from == calendar.startOfDay(for: now))
        #expect(showsModel.dateRange.to == calendar.startOfDay(for: now))
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

    @Test("shows discovery applies default nearby preference when no search location exists")
    func showsDiscoveryAppliesDefaultNearbyPreference() async throws {
        let showsModel = makeShowsListModel(
            name: "default-nearby",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        let preference = NearbyPreference(
            zipCode: "10801",
            source: .manual,
            distanceMiles: 25,
            city: "New Rochelle",
            state: "NY"
        )

        showsModel.applyDefaultNearbyPreference(preference)

        #expect(showsModel.activeNearbyPreference == preference)
        #expect(showsModel.zipCodeDraft == "10801")
        #expect(showsModel.requestKey.sanitizedZip == "10801")
        #expect(showsModel.requestKey.distance.rawValue == 25)
        #expect(showsModel.activeLocationLabel == "New Rochelle, NY")
    }

    @Test("shows discovery default nearby preference does not override local search location")
    func showsDiscoveryDefaultNearbyPreferenceDoesNotOverrideLocalLocation() async throws {
        let showsModel = makeShowsListModel(
            name: "default-nearby-preserves-local",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )

        showsModel.zipCodeDraft = "30309"
        showsModel.distance = .regional
        #expect(showsModel.applyManualZip())

        showsModel.applyDefaultNearbyPreference(
            NearbyPreference(zipCode: "10801", source: .manual, distanceMiles: 25)
        )

        #expect(showsModel.activeNearbyPreference == NearbyPreference(zipCode: "30309", source: .manual, distanceMiles: 50))
        #expect(showsModel.requestKey.sanitizedZip == "30309")
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
        let clubsModel = makeSearchClubsDiscoveryModel()
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
        #expect(showsModel.comedianSearchText == "")
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
        #expect(showsModel.comedianSearchText == "")
    }

    @Test("show search seed round-trips all faceted state")
    func showSearchSeedRoundTripsFacetedState() async throws {
        let showsModel = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )

        let dateRange = DateRangeFilter(
            from: Date(timeIntervalSince1970: 1_800_000_000),
            to: Date(timeIntervalSince1970: 1_800_086_400),
            isActive: true
        )
        let seed = ShowSearchSeed(
            comedian: "Atsuko Okatsuka",
            club: "The Stand",
            dateRange: dateRange,
            filterSlugs: ["free", "open_mic"],
            maximumPrice: .sixty,
            distance: .regional,
            resultsPresentation: .calendar
        )

        showsModel.applySearchSeed(seed)

        #expect(showsModel.comedianSearchText == "Atsuko Okatsuka")
        #expect(showsModel.clubSearchText == "The Stand")
        #expect(showsModel.selectedFilterSlugs == ["free", "open_mic"])
        #expect(showsModel.maximumPrice == .sixty)
        #expect(showsModel.distance == .regional)
        #expect(showsModel.resultsPresentation == .calendar)
        #expect(showsModel.makeSearchSeed() == seed)
    }

    @Test("show constraints are removable and clear together")
    func showConstraintsAreRemovableAndClearTogether() async throws {
        let showsModel = makeShowsListModel(
            name: "constraint-clear",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        showsModel.zipCodeDraft = "10012"
        #expect(showsModel.applyManualZip())
        showsModel.comedianSearchText = "Atsuko"
        showsModel.clubSearchText = "The Stand"
        showsModel.dateRange.isActive = true
        showsModel.selectedFilterSlugs = ["free", "improv"]
        showsModel.maximumPrice = .forty
        showsModel.resultsPresentation = .calendar

        let labels = showsModel.activeConstraints(availableFilters: []).map(\.label)
        #expect(labels.contains("Comedian: Atsuko"))
        #expect(labels.contains("Free"))
        #expect(labels.contains("Improv"))
        #expect(labels.contains("Up to $40"))

        showsModel.removeConstraint(.filter("free"))
        #expect(!showsModel.selectedFilterSlugs.contains("free"))

        showsModel.clearAllFilters()
        #expect(showsModel.activeConstraints(availableFilters: []).isEmpty)
        #expect(showsModel.comedianSearchText.isEmpty)
        #expect(showsModel.clubSearchText.isEmpty)
        #expect(showsModel.maximumPrice == .any)
        #expect(showsModel.resultsPresentation == .agenda)
    }

    @Test("default external show seed clears stale faceted state")
    func defaultExternalShowSeedClearsStaleFacetedState() async throws {
        let showsModel = makeShowsListModel(
            name: "default-external-seed",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        showsModel.comedianSearchText = "Atsuko"
        showsModel.clubSearchText = "The Stand"
        showsModel.dateRange.isActive = true
        showsModel.selectedFilterSlugs = ["free", "improv"]
        showsModel.maximumPrice = .forty
        showsModel.resultsPresentation = .calendar

        showsModel.applySearchSeed(ShowSearchSeed())

        #expect(showsModel.comedianSearchText.isEmpty)
        #expect(showsModel.clubSearchText.isEmpty)
        #expect(!showsModel.dateRange.isActive)
        #expect(showsModel.selectedFilterSlugs.isEmpty)
        #expect(showsModel.maximumPrice == .any)
        #expect(showsModel.resultsPresentation == .agenda)
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
private func makeSearchClubsDiscoveryModel() -> ClubsDiscoveryModel {
    ClubsDiscoveryModel(
        nearbyLocationController: NearbyLocationController(
            store: NearbyPreferenceStore(),
            resolver: StubNearbyLocationResolver(),
            zipLocationResolver: StubZipLocationResolver()
        )
    )
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
        StubURLProtocol.makeSession { request in
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
    }
}
