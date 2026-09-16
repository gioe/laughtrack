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
    @Test("search root keeps category entry visible and avoids duplicate Shows inputs")
    func searchRootKeepsCategoryEntryVisible() throws {
        let source = try String(contentsOf: searchRootViewSourceURL(), encoding: .utf8)

        #expect(source.contains("SearchQueryEntry("))
        let showsStart = try #require(source.range(of: "case .shows:\n            ShowsListView("))
        let comediansStart = try #require(source[showsStart.upperBound...].range(of: "case .comedians:"))
        let showsBlock = source[showsStart.lowerBound..<comediansStart.lowerBound]
        #expect(!showsBlock.contains("unifiedSearchText"))
        #expect(!showsBlock.contains("unifiedSearchPrompt"))
        #expect(showsBlock.contains("displaysSearchFields: false"))
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
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Comedian or club")
        #expect(SearchRootModel.Pivot.podcasts.queryPrompt == "Podcast title")
        #expect(ShowDistanceOption.allCases.map(\.title) == ["10 mi", "25 mi", "50 mi", "100 mi"])
        #expect(ShowSortOption.allCases.map(\.title) == ["Earliest", "Latest", "Low price", "High price"])
        #expect(!ShowSortOption.allCases.map(\.rawValue).contains("popularity_desc"))
        #expect(!showsModel.dateRange.isActive)

        model.activePivot = .podcasts
        model.query = "Comedy Cellar"
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
        showsModel.selectedFilterSlugs = [ShowFormatOption.openMic.rawValue]
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
        #expect(searchRootQueryValue("filters", from: request.path) == "open_mic")
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
        #expect(SearchRootModel.Pivot.shows.queryPrompt == "Comedian or club")
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

        model.activePivot = .clubs
        model.query = "Comedy Cellar"
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

        model.activePivot = .comedians
        model.query = "Atsuko"
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

        model.activePivot = .shows
        model.query = "Mark Normand"
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel,
            podcastsModel: podcastsModel
        )
        #expect(showsModel.comedianSearchText == "")
        #expect(showsModel.clubSearchText == "")

        model.activePivot = .podcasts
        model.query = "WTF"
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

    @Test("show constraints tolerate duplicate API filter slugs")
    func showConstraintsTolerateDuplicateAPIFilterSlugs() async throws {
        let showsModel = makeShowsListModel(
            name: "duplicate-filter-slugs",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        showsModel.selectedFilterSlugs = ["free"]
        let filters = [
            Components.Schemas.Filter(id: -1, slug: "free", name: "Free"),
            Components.Schemas.Filter(id: 9, slug: "free", name: "Legacy Free")
        ]

        let freeConstraints = showsModel.activeConstraints(availableFilters: filters).filter {
            $0.kind == .filter("free")
        }

        #expect(freeConstraints == [ShowActiveConstraint(kind: .filter("free"), label: "Free")])
    }

    @Test("legacy show filters remain visible and removable as active constraints")
    func legacyShowFiltersRemainVisibleAndRemovable() async throws {
        let showsModel = makeShowsListModel(
            name: "legacy-filter-constraints",
            resolver: MockSearchNearbyLocationResolver(result: .success("10012"))
        )
        showsModel.selectedFilterSlugs = ["open mic", "0-20"]
        let filters = [
            Components.Schemas.Filter(id: 7, slug: "open mic", name: "Open Mic"),
            Components.Schemas.Filter(id: 8, slug: "0-20", name: "$0–20"),
        ]

        let constraints = showsModel.activeConstraints(availableFilters: filters)

        #expect(constraints.contains(.init(kind: .filter("open mic"), label: "Open Mic")))
        #expect(constraints.contains(.init(kind: .filter("0-20"), label: "$0–20")))

        showsModel.removeConstraint(.filter("open mic"))
        showsModel.removeConstraint(.filter("0-20"))
        #expect(showsModel.selectedFilterSlugs.isEmpty)
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

@Suite("Search query continuity")
@MainActor
struct SearchQueryContinuityTests {
    @Test("editing and clearing a category preserves the other drafts")
    func editsAndClearAreCategoryLocal() {
        let root = SearchRootModel()
        let drafts: [(SearchRootModel.Pivot, String)] = [
            (.comedians, "  Ray DeVito  "), (.clubs, "Comedy Cellar"), (.podcasts, "WTF")
        ]
        for (pivot, text) in drafts {
            root.activePivot = pivot
            #expect(root.query.isEmpty)
            root.query = text
        }
        for (pivot, text) in drafts {
            root.activePivot = pivot
            #expect(root.query == text)
        }
        root.activePivot = .clubs
        root.query = ""
        #expect(root.query.isEmpty)
        root.activePivot = .comedians
        #expect(root.query == "  Ray DeVito  ")
        root.activePivot = .podcasts
        #expect(root.query == "WTF")
        root.activePivot = .clubs
        #expect(root.query.isEmpty)
    }

    @Test("applying a draft changes only the active category text")
    func applyingQueryPreservesOtherModelsAndFilters() {
        let root = SearchRootModel()
        let shows = makeShowsModel()
        let comedians = ComediansDiscoveryModel()
        let clubs = makeSearchClubsDiscoveryModel()
        let podcasts = PodcastSearchModel(fetcher: RecordingPodcastSearchFetcher())
        comedians.selectedFilterSlugs = ["improv"]
        shows.comedianSearchText = "Atsuko"
        shows.clubSearchText = "The Stand"
        shows.maximumPrice = .forty
        root.activePivot = .comedians
        root.query = "  Ray DeVito  "
        root.applyQuery(showsModel: shows, comediansModel: comedians, clubsModel: clubs, podcastsModel: podcasts)
        #expect(comedians.requestKey.text == "Ray DeVito")
        #expect(comedians.selectedFilterSlugs == ["improv"])
        root.query = ""
        root.applyQuery(showsModel: shows, comediansModel: comedians, clubsModel: clubs, podcastsModel: podcasts)
        #expect(comedians.searchText.isEmpty)
        #expect(comedians.selectedFilterSlugs == ["improv"])
        #expect(clubs.searchText.isEmpty)
        #expect(podcasts.searchText.isEmpty)
        #expect(shows.comedianSearchText == "Atsuko")
        #expect(shows.clubSearchText == "The Stand")
        #expect(shows.maximumPrice == .forty)
    }

    @Test("Discover seeds reset only their destination category draft")
    func discoverSeedsAreDestinationLocal() {
        let root = SearchRootModel()
        root.activePivot = .comedians
        root.query = "Ray"
        root.activePivot = .clubs
        root.query = "Cellar"
        root.activePivot = .podcasts
        root.query = "WTF"
        root.applySeed(.discoverEntity(.clubs))
        #expect(root.activePivot == .clubs)
        #expect(root.query.isEmpty)
        root.activePivot = .comedians
        #expect(root.query == "Ray")
        root.activePivot = .podcasts
        #expect(root.query == "WTF")
        root.applySeed(.init(pivot: .comedians, query: "Atsuko", shortcut: nil))
        #expect(root.query == "Atsuko")
        root.activePivot = .podcasts
        #expect(root.query == "WTF")
    }

    @Test("Shows seeds and explicit entity drafts stay separate from other categories")
    func showsSeedsPreserveEntityCategoryDrafts() {
        let root = SearchRootModel()
        let shows = makeShowsModel()
        root.activePivot = .comedians
        root.query = "Ray"
        let seed = SearchRootModel.Seed(
            pivot: .shows,
            query: "ignored generic query",
            shortcut: nil,
            showSearch: ShowSearchSeed(comedian: "Atsuko", club: "The Stand", maximumPrice: .forty)
        )
        root.applySeed(seed)
        shows.applySearchSeed(seed.showSearch)
        #expect(root.query.isEmpty)
        #expect(shows.comedianSearchText == "Atsuko")
        #expect(shows.clubSearchText == "The Stand")
        #expect(shows.maximumPrice == .forty)
        root.activePivot = .clubs
        root.query = "Cellar"
        root.activePivot = .shows
        #expect(shows.comedianSearchText == "Atsuko")
        #expect(shows.clubSearchText == "The Stand")
        root.activePivot = .comedians
        #expect(root.query == "Ray")
    }

    @Test("removing either Shows entity keeps the other entity and advanced constraints")
    func showEntityRemovalIsIndependent() {
        let shows = makeShowsModel()
        shows.comedianSearchText = "Atsuko"
        shows.clubSearchText = "The Stand"
        shows.maximumPrice = .forty
        shows.selectedFilterSlugs = ["improv"]
        shows.distance = .regional
        let initialDateRange = shows.dateRange
        #expect(shows.activeConstraints(availableFilters: []).contains { $0.kind == .comedian && $0.label == "Comedian: Atsuko" })
        #expect(shows.activeConstraints(availableFilters: []).contains { $0.kind == .club && $0.label == "Club: The Stand" })
        shows.removeConstraint(.comedian)
        #expect(shows.comedianSearchText.isEmpty)
        #expect(shows.clubSearchText == "The Stand")
        #expect(!shows.activeConstraints(availableFilters: []).contains { $0.kind == .comedian })
        shows.comedianSearchText = "Ray"
        shows.removeConstraint(.club)
        #expect(shows.clubSearchText.isEmpty)
        #expect(shows.comedianSearchText == "Ray")
        #expect(!shows.activeConstraints(availableFilters: []).contains { $0.kind == .club })
        #expect(shows.maximumPrice == .forty)
        #expect(shows.selectedFilterSlugs == ["improv"])
        #expect(shows.distance == .regional)
        #expect(shows.dateRange == initialDateRange)
    }

    private func makeShowsModel() -> ShowsListModel {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "query-continuity")
        return ShowsListModel(
            nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store),
            initialUseDateRange: false
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

@Suite("Shows search header behavior")
@MainActor
struct SearchShowsHeaderTests {
    private var calendar: Calendar {
        var value = Calendar(identifier: .gregorian)
        value.timeZone = TimeZone(secondsFromGMT: 0)!
        return value
    }

    private func date(_ day: Int) -> Date {
        calendar.date(from: DateComponents(year: 2030, month: 4, day: day, hour: 18))!
    }

    private func makeModel(pinnedClubId: Int? = nil, pinnedComedianName: String? = nil) -> ShowsListModel {
        let defaults = UserDefaults(suiteName: "SearchShowsHeaderTests.\(UUID().uuidString)")!
        return ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults)),
                resolver: MockSearchNearbyLocationResolver(result: .success("10012")),
                zipLocationResolver: StubZipLocationResolver()
            ),
            pinnedClubId: pinnedClubId,
            pinnedComedianName: pinnedComedianName,
            initialUseDateRange: false,
            startsWithNearbyLocation: false
        )
    }

    @Test("Tonight narrows dates without clearing advanced constraints")
    func tonightPreservesOtherConstraints() {
        let model = makeModel()
        model.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
        model.clubSearchText = "Comedy Cellar"
        model.selectedFilterSlugs = ["standup", "clean"]
        model.maximumPrice = .forty
        model.sort = .premium

        model.applyDateShortcut("Tonight", now: date(2), calendar: calendar)

        #expect(model.dateRange.from == calendar.startOfDay(for: date(2)))
        #expect(model.dateRange.to == model.dateRange.from)
        #expect(model.dateRange.isActive)
        #expect(model.sort == .earliest)
        #expect(model.requestKey.sanitizedZip == "10012")
        #expect(model.requestKey.distance == .regional)
        #expect(model.requestKey.club == "Comedy Cellar")
        #expect(model.requestKey.filters == ["clean", "standup"])
        #expect(model.requestKey.maximumPrice == 40)
    }

    @Test("This weekend starts Friday or today and ends Sunday", arguments: [2, 5, 6, 7])
    func weekendExcludesElapsedDays(day: Int) {
        let model = makeModel()
        model.applyDateShortcut("This Weekend", now: date(day), calendar: calendar)

        #expect(model.dateRange.from == calendar.startOfDay(for: date(max(day, 5))))
        #expect(model.dateRange.to == calendar.startOfDay(for: date(7)))
        #expect(model.dateRange.isActive)
        #expect(model.sort == .earliest)
    }

    @Test("Any date clears only the date constraint and restores chronological order")
    func anyDatePreservesOtherConstraints() {
        let model = makeModel()
        model.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 10))
        model.clubSearchText = "The Stand"
        model.selectedFilterSlugs = ["free"]
        model.maximumPrice = .twenty
        model.resultsPresentation = .calendar
        model.applyDateShortcut("Tonight", now: date(2), calendar: calendar)
        model.sort = .budget

        model.applyDateShortcut("Any date", now: date(2), calendar: calendar)

        #expect(!model.dateRange.isActive)
        #expect(model.requestKey.fromString == nil)
        #expect(model.requestKey.toString == nil)
        #expect(model.sort == .earliest)
        #expect(model.requestKey.sanitizedZip == "10012")
        #expect(model.requestKey.distance == .nearby)
        #expect(model.requestKey.club == "The Stand")
        #expect(model.requestKey.filters == ["free"])
        #expect(model.requestKey.maximumPrice == 20)
        #expect(model.resultsPresentation == .calendar)
    }

    @Test("Changing radius and ZIP keeps the search local override after clearing")
    func locationAndRadiusRemainSearchLocal() {
        let model = makeModel()
        let shared = NearbyPreference(zipCode: "94108", source: .manual, distanceMiles: 25)
        model.applyDefaultNearbyPreference(shared)
        model.distance = .roadTrip
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        model.applyDefaultNearbyPreference(shared)

        #expect(model.activeNearbyPreference?.zipCode == "10012")
        #expect(model.activeNearbyPreference?.distanceMiles == 100)
        #expect(model.requestKey.distance == .roadTrip)
        model.clearLocation()
        model.applyDefaultNearbyPreference(shared)
        #expect(model.activeNearbyPreference == nil)
        #expect(model.requestKey.sanitizedZip == nil)
    }

    @Test("Price and facets can be removed independently without clearing dates")
    func advancedConstraintsRemainIndependent() {
        let model = makeModel()
        model.applyDateShortcut("Tonight", now: date(2), calendar: calendar)
        model.selectedFilterSlugs = ["standup", "clean"]
        model.maximumPrice = .sixty
        model.removeConstraint(.maximumPrice)
        #expect(model.requestKey.maximumPrice == nil)
        #expect(model.selectedFilterSlugs == ["standup", "clean"])
        model.maximumPrice = .twenty
        model.removeConstraint(.filter("clean"))
        #expect(model.requestKey.filters == ["standup"])
        #expect(model.requestKey.maximumPrice == 20)
        #expect(model.dateRange.isActive)
    }

    @Test("Pinned club remains identified by ID and ignores search location")
    func pinnedClubPreservesScope() {
        let model = makeModel(pinnedClubId: 42)
        model.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
        model.applySearchSeed(.init(club: "A different club", filterSlugs: ["free"], maximumPrice: .forty))
        model.applyDateShortcut("Tonight", now: date(2), calendar: calendar)
        #expect(!model.allowsLocationFiltering)
        #expect(model.requestKey.clubId == 42)
        #expect(model.requestKey.club.isEmpty)
        #expect(model.requestKey.sanitizedZip == nil)
        model.clearAllFilters()
        #expect(model.requestKey.clubId == 42)
        #expect(model.requestKey.club.isEmpty)
        #expect(model.requestKey.filters.isEmpty)
    }

    @Test("Pinned comedian survives seeds and reset while retaining nearby filtering")
    func pinnedComedianPreservesScope() {
        let model = makeModel(pinnedComedianName: "Atsuko Okatsuka")
        model.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
        model.applySearchSeed(.init(comedian: "Someone else", maximumPrice: .forty))
        #expect(model.requestKey.comedian == "Atsuko Okatsuka")
        #expect(model.requestKey.sanitizedZip == "10012")
        #expect(!model.isShowingNationwideComedianSearch)
        model.clearAllFilters()
        #expect(model.requestKey.comedian == "Atsuko Okatsuka")
        #expect(model.requestKey.maximumPrice == nil)
    }

    @Test("Discover Tonight seed retains location and advanced search values")
    func discoverSeedRetainsSearchValues() {
        let root = SearchRootModel()
        let model = makeModel()
        let seed = SearchRootModel.Seed(
            pivot: .shows, query: "", shortcut: "Tonight",
            nearbyPreference: .init(zipCode: "10012", source: .manual, distanceMiles: 50),
            showSearch: .init(club: "Comedy Cellar", filterSlugs: ["standup"], maximumPrice: .forty,
                              distance: .regional, resultsPresentation: .calendar)
        )
        root.applySeed(seed)
        model.applySearchSeedNearbyPreference(seed.nearbyPreference)
        model.applySearchSeed(seed.showSearch)
        root.applyShortcutFilters(to: model, now: date(2), calendar: calendar)

        #expect(root.activePivot == .shows)
        #expect(model.requestKey.club == "Comedy Cellar")
        #expect(model.requestKey.filters == ["standup"])
        #expect(model.requestKey.maximumPrice == 40)
        #expect(model.requestKey.sanitizedZip == "10012")
        #expect(model.requestKey.distance == .regional)
        #expect(model.dateRange.from == calendar.startOfDay(for: date(2)))
        #expect(model.dateRange.to == model.dateRange.from)
        #expect(model.dateRange.isActive)
        #expect(model.resultsPresentation == .calendar)
        #expect(model.makeSearchSeed().club == "Comedy Cellar")
    }
}

#if canImport(UIKit)
import UIKit

@MainActor
private final class ShowsFilterSheetTestState: ObservableObject {
    @Published var slugs: Set<String> = ["standup"]
    @Published var price: ShowMaximumPriceOption = .forty
    @Published var isMounted = true
    var didAppear = false
    var didDisappear = false
}

@MainActor
private struct ShowsFilterSheetTestRoot: View {
    @ObservedObject var state: ShowsFilterSheetTestState
    var size: DynamicTypeSize = .large
    var filters: [Components.Schemas.Filter] = [
        .init(id: 1, slug: "standup", name: "Stand-up"),
        .init(id: 2, slug: "clean", name: "Clean comedy"),
        .init(id: 3, slug: "free", name: "Free")
    ]

    var body: some View {
        Group {
            if state.isMounted {
                SearchFilterModal(
                    filters: filters, selectedSlugs: $state.slugs,
                    isPresented: $state.isMounted, maximumPrice: $state.price,
                    preview: { _ in .success(12) }
                )
                .onAppear { state.didAppear = true }
                .onDisappear { state.didDisappear = true }
            } else {
                Color.clear
            }
        }
        .environment(\.appTheme, LaughTrackTheme())
        .environment(\.dynamicTypeSize, size)
        .preferredColorScheme(.dark)
    }
}

@Suite("Shows filter sheets", .serialized)
@MainActor
struct SearchShowsFilterSheetTests {
    @Test("Dismissing Filters does not overwrite external parent changes")
    func dismissPreservesExternalChanges() async throws {
        let state = ShowsFilterSheetTestState()
        let host = HostedView(ShowsFilterSheetTestRoot(state: state), freshWindow: true)
        try await waitFor(host) { state.didAppear }
        state.slugs = ["free", "clean"]
        state.price = .twenty
        host.render()
        #expect(state.slugs == ["free", "clean"])
        #expect(state.price == .twenty)

        state.isMounted = false
        try await waitFor(host) {
            state.didDisappear && state.slugs == ["free", "clean"] && state.price == .twenty
        }
        #expect(state.slugs == ["free", "clean"])
        #expect(state.price == .twenty)
    }

    @Test("Dismissing a price-only sheet preserves external price changes")
    func dismissPreservesExternalPrice() async throws {
        let state = ShowsFilterSheetTestState()
        state.slugs = []
        let host = HostedView(ShowsFilterSheetTestRoot(state: state, filters: []), freshWindow: true)
        try await waitFor(host) { state.didAppear }
        state.price = .any
        host.render()
        #expect(state.price == .any)
        state.isMounted = false
        try await waitFor(host) { state.didDisappear && state.price == .any }
        #expect(state.slugs.isEmpty)
        #expect(state.price == .any)
    }

    @Test("Capture location radius and advanced Filters at standard and accessibility sizes")
    func captureSheets() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            let state = ShowsFilterSheetTestState()
            let filterHost = HostedView(ShowsFilterSheetTestRoot(state: state, size: size), freshWindow: true)
            try await waitFor(filterHost) { state.didAppear }
            try capture(filterHost, name: "filters-top", size: size)
            filterHost.scrollDown(pages: 1)
            filterHost.render()
            try capture(filterHost, name: "filters-scrolled", size: size)
            state.isMounted = false
            try await waitFor(filterHost) { state.didDisappear }

            let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "header-location-sheet")
            let model = ShowsListModel(
                nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store),
                initialUseDateRange: false, startsWithNearbyLocation: false
            )
            model.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
            var appeared = false
            let locationHost = HostedView(
                LocationFilterSheet(
                    model: model, isPresented: .constant(true),
                    distance: Binding(get: { model.distance }, set: { model.distance = $0 })
                )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.dynamicTypeSize, size)
                .preferredColorScheme(.dark)
                .onAppear { appeared = true },
                freshWindow: true
            )
            try await waitFor(locationHost) { appeared }
            try capture(locationHost, name: "location-top", size: size)
            locationHost.scrollDown(pages: 1)
            locationHost.render()
            try capture(locationHost, name: "location-scrolled", size: size)
        }
    }

    private func waitFor(_ host: HostedView, condition: () -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(3)
        while !condition(), ContinuousClock.now < deadline {
            await Task.yield()
            host.render()
        }
        try #require(condition(), "Expected the sheet lifecycle and binding updates to complete")
    }

    private func capture(_ host: HostedView, name: String, size: DynamicTypeSize) throws {
        let data = try #require(try host.snapshot().pngData())
        let device = UIDevice.current.userInterfaceIdiom == .pad ? "ipad" : "phone"
        let textSize = size.isAccessibilitySize ? "AX5" : "standard"
        let path = FileManager.default.temporaryDirectory
            .appendingPathComponent("task4001-\(device)-\(textSize)-\(name).png")
        try data.write(to: path)
        print("Shows sheet capture: \(path.path)")
        #if compiler(>=6.2)
        Attachment.record(Array(data), named: path.lastPathComponent)
        #endif
    }
}
#endif

@Suite("Search filter drafts", .serialized)
@MainActor
struct SearchFilterDraftTests {
    @Test("Draft previews isolate the parent, Apply commits once, and reopening seeds committed choices")
    func applyOnce() async {
        var parent = SearchFilterDraft.Selection(slugs: ["standup"], maximumPrice: .forty)
        var commits = 0
        var requests: [SearchFilterDraft.Selection] = []
        let draft = SearchFilterDraft(filters: [], selection: parent) { selection in
            requests.append(selection)
            return .success(7)
        }
        draft.toggle("clean")
        draft.update(.init(slugs: draft.selection.slugs, maximumPrice: .twenty))
        await draft.refreshPreview(debounce: false)
        #expect(parent == .init(slugs: ["standup"], maximumPrice: .forty))
        #expect(requests == [.init(slugs: ["standup", "clean"], maximumPrice: .twenty)])
        #expect(draft.preview == .ready(7))
        let commit: (SearchFilterDraft.Selection) -> Void = { parent = $0; commits += 1 }
        draft.apply(commit)
        draft.apply(commit)
        draft.close() // onDisappear must not undo Apply.
        #expect(commits == 1)
        #expect(parent == .init(slugs: ["standup", "clean"], maximumPrice: .twenty))
        let reopened = SearchFilterDraft(filters: [], selection: parent) { _ in .success(7) }
        #expect(reopened.selection == parent)
    }

    @Test("Close or swipe cancellation discards reset and price changes, even with a late response")
    func cancelAndReopen() async {
        let parent = SearchFilterDraft.Selection(slugs: ["standup"], maximumPrice: .forty)
        var continuation: CheckedContinuation<Result<Int, LoadFailure>, Never>?
        let draft = SearchFilterDraft(filters: [], selection: parent) { _ in
            await withCheckedContinuation { continuation = $0 }
        }
        draft.update(.init(slugs: []))
        let request = Task { await draft.refreshPreview(debounce: false) }
        while continuation == nil { await Task.yield() }
        draft.close()
        continuation?.resume(returning: .success(900))
        await request.value
        var commits = 0
        draft.apply { _ in commits += 1 }
        #expect(commits == 0)
        #expect(draft.preview == .updating)
        let reopened = SearchFilterDraft(filters: [], selection: parent) { _ in .success(12) }
        #expect(reopened.selection == .init(slugs: ["standup"], maximumPrice: .forty))
    }

    @Test("Late responses cannot replace the latest count, including an A to B to A sequence")
    func staleResponses() async {
        var continuations: [CheckedContinuation<Result<Int, LoadFailure>, Never>] = []
        let draft = SearchFilterDraft(filters: [], selection: .init(slugs: ["standup"])) { _ in
            await withCheckedContinuation { continuations.append($0) }
        }
        let first = Task { await draft.refreshPreview(debounce: false) }
        while continuations.count < 1 { await Task.yield() }
        draft.toggle("clean")
        let second = Task { await draft.refreshPreview(debounce: false) }
        while continuations.count < 2 { await Task.yield() }
        draft.toggle("clean")
        let third = Task { await draft.refreshPreview(debounce: false) }
        while continuations.count < 3 { await Task.yield() }
        continuations[2].resume(returning: .success(3))
        await third.value
        continuations[1].resume(returning: .failure(.network("Offline")))
        continuations[0].resume(returning: .success(500))
        await second.value
        await first.value
        #expect(draft.preview == .ready(3))
    }

    @Test("Only confirmed zero is shown as zero; pending and failed requests have honest status")
    func countStatesAndStableFacets() async {
        let filters: [Components.Schemas.Filter] = [
            .init(id: 1, slug: "clean", name: "Clean comedy"),
            .init(id: 2, slug: "standup", name: "Stand-up")
        ]
        var response: Result<Int, LoadFailure> = .success(0)
        let draft = SearchFilterDraft(filters: filters, selection: .init(slugs: [])) { _ in response }
        #expect(draft.preview.message == "Updating results…")
        await draft.refreshPreview(debounce: false)
        #expect(draft.preview.message == "0 results")
        draft.toggle("clean")
        #expect(draft.preview.message == "Updating results…")
        response = .failure(.network("Offline"))
        await draft.refreshPreview(debounce: false)
        #expect(draft.preview.message == "Preview unavailable")
        #expect(draft.filters.map(\.slug) == ["clean", "standup"])
        draft.retry()
        #expect(draft.preview == .updating)
        response = .success(1)
        await draft.refreshPreview(debounce: false)
        #expect(draft.preview.message == "1 result")
    }

    @Test("Rapid toggles debounce into one preview and keep selection with empty facets")
    func rapidToggles() async {
        var requests: [SearchFilterDraft.Selection] = []
        let draft = SearchFilterDraft(filters: [], selection: .init(slugs: ["unknown"])) { selection in
            requests.append(selection)
            return .success(2)
        }
        let first = Task { await draft.refreshPreview() }
        await Task.yield()
        draft.toggle("clean")
        let second = Task { await draft.refreshPreview() }
        await Task.yield()
        draft.toggle("standup")
        let third = Task { await draft.refreshPreview() }
        await first.value
        await second.value
        await third.value
        #expect(requests == [.init(slugs: ["unknown", "clean", "standup"])])
        #expect(draft.filters.isEmpty)
    }

    #if canImport(UIKit)
    @Test("Capture empty-facet zero and failed previews at standard and accessibility text sizes")
    func capturePreviewStates() async throws {
        for size in [DynamicTypeSize.large, .accessibility5] {
            for fails in [false, true] {
                let host = HostedView(
                    SearchFilterModal(
                        filters: [], selectedSlugs: .constant([]), isPresented: .constant(true),
                        preview: { _ in fails ? .failure(.network("Offline")) : .success(0) }
                    )
                    .environment(\.appTheme, LaughTrackTheme())
                    .environment(\.dynamicTypeSize, size)
                    .preferredColorScheme(.dark),
                    freshWindow: true
                )
                await host.settle(iterations: 30)
                let data = try #require(host.snapshot().pngData())
                let device = UIDevice.current.userInterfaceIdiom == .pad ? "ipad" : "phone"
                let textSize = size.isAccessibilitySize ? "AX5" : "standard"
                let state = fails ? "failed" : "zero"
                let path = FileManager.default.temporaryDirectory
                    .appendingPathComponent("task4009-\(device)-\(textSize)-\(state).png")
                try data.write(to: path)
                print("Filter preview capture: \(path.path)")
                #if compiler(>=6.2)
                Attachment.record(Array(data), named: path.lastPathComponent)
                #endif
            }
        }
    }
    #endif

    @Test("All preview endpoints preserve captured context without changing the parent query or results")
    func previewAdapters() async throws {
        let transport = StubClientTransport { _, _, _, _ in
            var response = HTTPResponse(status: .ok)
            response.headerFields[.contentType] = "application/json"
            return (response, HTTPBody(#"{"data":[],"total":9,"filters":[],"homeCityFilters":[],"zipCapTriggered":true}"#))
        }
        let client = Client(serverURL: URL(string: "https://example.test")!, transport: transport)
        let draft = SearchFilterDraft.Selection(slugs: ["clean", "standup"], maximumPrice: .twenty)
        let comedians = ComediansDiscoveryModel()
        comedians.searchText = "Ray"
        comedians.homeCity = "New York|NY"
        comedians.includeEmpty = true
        let comedianQuery = comedians.requestKey
        let comedianPreview = comedians.makeFilterPreview(apiClient: client)
        let comedianCount = await comedianPreview(draft)
        #expect(try comedianCount.get() == 9)
        #expect(comedians.requestKey == comedianQuery)
        if case .success = comedians.phase { Issue.record("Preview replaced parent results") }

        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "filter-preview")
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
        let clubs = ClubsDiscoveryModel(nearbyLocationController: controller)
        clubs.searchText = "Cellar"
        clubs.includeEmpty = true
        clubs.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
        let clubQuery = clubs.requestKey
        let clubCount = await clubs.makeFilterPreview(apiClient: client)(draft)
        #expect(try clubCount.get() == 9)
        #expect(clubs.requestKey == clubQuery)
        if case .success = clubs.phase { Issue.record("Preview replaced parent results") }

        let shows = ShowsListModel(nearbyLocationController: controller, initialUseDateRange: false, startsWithNearbyLocation: false)
        shows.applySearchSeedNearbyPreference(.init(zipCode: "10012", source: .manual, distanceMiles: 50))
        let showQuery = shows.requestKey
        let showCount = await shows.makeFilterPreview(apiClient: client)(draft)
        #expect(try showCount.get() == 9)
        #expect(shows.requestKey == showQuery)
        #expect(!shows.zipCapTriggered)
        if case .success = shows.phase { Issue.record("Preview replaced parent results") }

        let requests = transport.capturedRequests
        #expect(requests.count == 3)
        func params(_ index: Int) throws -> [String: String] {
            let path = try #require(transport.capturedRequests[index].path)
            let url = try #require(URLComponents(string: "https://example.test\(path)"))
            return Dictionary(uniqueKeysWithValues: (url.queryItems ?? []).map { ($0.name, $0.value ?? "") })
        }
        let comedianParams = try params(0)
        #expect(comedianParams["comedian"] == "Ray")
        #expect(comedianParams["homeCity"] == "New York|NY")
        #expect(comedianParams["includeEmpty"] == "true")
        let clubParams = try params(1)
        #expect(clubParams["club"] == "Cellar")
        #expect(clubParams["zip"] == "10012")
        #expect(clubParams["distance"] == "50")
        let showParams = try params(2)
        #expect(showParams["maxPrice"].flatMap(Double.init) == 20)
        #expect(showParams["dateBasis"] == "venue")
        #expect(showParams["zip"] == "10012")
        for index in 0..<3 {
            #expect(try params(index)["filters"] == "clean,standup")
            #expect(try params(index)["page"] == "1")
        }
        // A captured preview remains scoped to the presentation's initial query.
        comedians.searchText = "Changed elsewhere"
        _ = await comedianPreview(draft)
        #expect(try params(3)["comedian"] == "Ray")
    }
}
