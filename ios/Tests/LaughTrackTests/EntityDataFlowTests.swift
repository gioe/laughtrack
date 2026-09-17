import Foundation
import Combine
import SwiftUI
#if canImport(UIKit)
import UIKit
#endif
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Entity data flow")
@MainActor
struct EntityDataFlowTests {
    @Test("entity navigation targets map to the expected app routes")
    func navigationTargetsMapToRoutes() {
        #expect(EntityNavigationTarget.show(7).route == .showDetail(7))
        #expect(EntityNavigationTarget.comedian(8).route == .comedianDetail(8))
        #expect(EntityNavigationTarget.club(9).route == .clubDetail(9))
    }

    @Test("home trending comedians keeps no-photo entries behind ten photo-backed entries")
    func homeTrendingComediansPrioritizesPhotoBackedEntries() {
        let comedians = makeTrendingComedians(photoCount: 10, includesNoPhoto: true)
        let railItems = HomeTrendingComediansModel.railItems(from: comedians)

        #expect(railItems.prefix(10).allSatisfy { !$0.imageUrl.isEmpty })
        #expect(railItems[10].imageUrl.isEmpty)
    }

    @Test("home trending comedians with fewer than ten photos hides no-photo entries")
    func homeTrendingComediansHidesNoPhotoEntriesBeforeFirstPageIsFull() {
        let comedians = makeTrendingComedians(photoCount: 9, includesNoPhoto: true)
        let railItems = HomeTrendingComediansModel.railItems(from: comedians)

        #expect(railItems.count == 9)
        #expect(railItems.allSatisfy { !$0.imageUrl.isEmpty })
    }

    @Test("search model standardizes reload and load more pagination")
    func searchModelReloadAndLoadMore() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "clubs") { page, query in
            #expect(page == 0)
            #expect(query == "clubs")
            return .success(.init(items: [10, 11], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11])
            #expect(page.total == 4)
            #expect(page.page == 0)
        default:
            Issue.record("Expected reload to finish in a success phase")
        }

        await model.loadMore(query: "clubs") { page, query in
            #expect(page == 1)
            #expect(query == "clubs")
            return .success(.init(items: [12, 13], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11, 12, 13])
            #expect(page.total == 4)
            #expect(page.page == 1)
        default:
            Issue.record("Expected loadMore to preserve and append results")
        }
    }

    @Test("search model replaces results when navigating to a numbered page")
    func searchModelLoadsNumberedPage() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "shows") { _, _ in
            .success(.init(items: [1, 2], total: 4))
        }
        await model.loadPage(1, query: "shows") { page, query in
            #expect(page == 1)
            #expect(query == "shows")
            return .success(.init(items: [3, 4], total: 4))
        }

        guard case .success(let page) = model.phase else {
            Issue.record("Expected numbered pagination to retain a success phase")
            return
        }
        #expect(page.items == [3, 4])
        #expect(page.total == 4)
        #expect(page.page == 1)
    }

    @Test("search model keeps prior results and surfaces pagination failures")
    func searchModelKeepsResultsOnPaginationFailure() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "shows") { _, _ in
            .success(.init(items: [1, 2], total: 3))
        }

        await model.loadMore(query: "shows") { _, _ in
            .failure(.network("Timed out"))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [1, 2])
            #expect(page.page == 0)
        default:
            Issue.record("Expected prior success page to remain after pagination failure")
        }

        #expect(model.paginationFailure == .network("Timed out"))
    }

    @Test("search model clears loading state when a debounced reload is cancelled")
    func searchModelClearsLoadingStateWhenDebouncedReloadIsCancelled() async throws {
        let model = EntitySearchModel<String, Int>()

        let cancelledReload = Task {
            await model.reload(query: "nearby", shouldDebounce: true) { _, _ in
                Issue.record("Cancelled debounced reload should not reach fetch")
                return .success(.init(items: [], total: 0))
            }
        }

        try await Task.sleep(for: .milliseconds(100))
        cancelledReload.cancel()
        await cancelledReload.value

        await model.reload(query: "nearby") { page, query in
            #expect(page == 0)
            #expect(query == "nearby")
            return .success(.init(items: [42], total: 1))
        }

        guard case .success(let page) = model.phase else {
            Issue.record("Expected cancelled debounce to allow a future reload")
            return
        }
        #expect(page.items == [42])
    }

    @Test("search model allows same-query reload after an in-flight reload is cancelled")
    func searchModelAllowsSameQueryReloadAfterInFlightReloadIsCancelled() async throws {
        let model = EntitySearchModel<String, Int>()
        let firstFetchStarted = AsyncStream<Void>.makeStream()

        let cancelledReload = Task {
            await model.reload(query: "tonight", shouldDebounce: true) { _, _ in
                firstFetchStarted.continuation.yield(())
                try? await Task.sleep(for: .milliseconds(200))
                return .success(.init(items: [1], total: 1))
            }
        }

        for await _ in firstFetchStarted.stream {
            break
        }
        cancelledReload.cancel()

        await model.reload(query: "tonight") { page, query in
            #expect(page == 0)
            #expect(query == "tonight")
            return .success(.init(items: [42], total: 1))
        }
        await cancelledReload.value

        guard case .success(let page) = model.phase else {
            Issue.record("Expected same-query reload to recover from the cancelled in-flight load")
            return
        }
        #expect(page.items == [42])
    }

    @Test("home shows tonight model renders raw API show dates from a 200 home feed")
    func homeShowsTonightModelDecodesRawHomeFeedDates() async {
        let model = HomeShowsTonightModel()
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: RawShowRailTransport()
        )

        await model.refresh(
            apiClient: client,
            zipCode: nil,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected home shows tonight to decode the 200 home feed")
            return
        }

        #expect(shows.map(\.id) == [101])
        #expect(model.cityTitle == "New York, NY")
    }

    @Test("home show rails hide sold-out shows")
    func homeShowRailsHideSoldOutShows() async {
        let model = HomeShowsTonightModel()
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: RawShowRailTransport()
        )

        await model.refresh(
            apiClient: client,
            zipCode: nil,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected home shows tonight to decode the 200 home feed")
            return
        }

        #expect(shows.map(\.id) == [101])
        #expect(shows.allSatisfy { $0.soldOut != true })
    }

    @Test("shows discovery model renders raw API show dates from a 200 search response")
    func showsDiscoveryModelDecodesRawSearchDates() async {
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: RawShowRailTransport()
        )

        await model.reload(apiClient: client)

        guard case .success(let page) = model.phase else {
            Issue.record("Expected shows discovery to decode the 200 search response")
            return
        }

        #expect(page.items.map(\.id) == [201])
        #expect(page.total == 1)
    }

    @Test("shows discovery model hides sold-out shows")
    func showsDiscoveryModelHidesSoldOutShows() async {
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: RawShowRailTransport()
        )

        await model.reload(apiClient: client)

        guard case .success(let page) = model.phase else {
            Issue.record("Expected shows discovery to decode the 200 search response")
            return
        }

        #expect(page.items.map(\.id) == [201])
        #expect(page.items.allSatisfy { $0.soldOut != true })
    }

    @Test("shows discovery model sends selected filter slugs and stores returned filter options")
    func showsDiscoveryModelSendsSelectedFilters() async {
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchShows")
            return testJSONResponse(
                """
                {
                  "data": [],
                  "total": 0,
                  "filters": [
                    { "id": 1, "slug": "late-night", "name": "Late night", "selected": true },
                    { "id": 2, "slug": "stand-up", "name": "Stand-up", "selected": true }
                  ],
                  "zipCapTriggered": false
                }
                """
            )
        }
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        model.selectedFilterSlugs = ["stand-up", "late-night"]
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        await model.reload(apiClient: client)

        let filtersParam = queryValue("filters", from: transport.capturedRequests.last?.path)
        #expect(filtersParam == "late-night,stand-up")

        guard case .success(let page) = model.phase else {
            Issue.record("Expected shows discovery to retain a success page")
            return
        }
        #expect(page.filters.map(\.slug) == ["late-night", "stand-up"])
    }

    @Test("shows discovery model relaxes nearby radius for comedian searches")
    func showsDiscoveryModelRelaxesNearbyRadiusForComedianSearches() async {
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchShows")
            return testJSONResponse(
                """
                {
                  "data": [],
                  "total": 0,
                  "filters": [],
                  "zipCapTriggered": false
                }
                """
            )
        }
        let store = NearbyPreferenceStore()
        store.setManualZip("90028", distanceMiles: 100)
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: store,
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        model.comedianSearchText = "Christina P"
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        await model.reload(apiClient: client)

        let path = transport.capturedRequests.last?.path
        #expect(queryValue("comedian", from: path) == "Christina P")
        #expect(queryValue("zip", from: path) == nil)
        #expect(queryValue("distance", from: path) == nil)
        #expect(model.isShowingNationwideComedianSearch)
    }

    @Test("shows discovery model can pin show searches to a club")
    func showsDiscoveryModelPinsSearchesToClub() async {
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchShows")
            return testJSONResponse(
                """
                {
                  "data": [],
                  "total": 0,
                  "filters": [],
                  "zipCapTriggered": false
                }
                """
            )
        }
        let suiteName = "EntityDataFlowTests.pinned-club.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let nearbyStore = NearbyPreferenceStore(
            appStateStorage: AppStateStorage(userDefaults: defaults)
        )
        nearbyStore.setManualZip(
            "90028",
            distanceMiles: 25,
            city: "Los Angeles",
            state: "CA"
        )
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: nearbyStore,
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            pinnedClubName: "Comedy Cellar"
        )
        model.clubSearchText = "The Stand"
        model.comedianSearchText = "Mark Normand"
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        await model.reload(apiClient: client)

        let path = transport.capturedRequests.last?.path
        #expect(model.isClubPinned)
        #expect(!model.allowsLocationFiltering)
        #expect(!model.activeConstraints(availableFilters: []).contains { constraint in
            constraint.kind == .location
        })
        #expect(queryValue("club", from: path) == "Comedy Cellar")
        #expect(queryValue("comedian", from: path) == "Mark Normand")
    }

    @Test("shows discovery model defaults date filtering to today")
    func showsDiscoveryModelDefaultsDateFilteringToToday() {
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )

        #expect(model.dateRange.isActive)
        #expect(model.dateRange.pillLabel() == "Today")
        #expect(model.requestKey.fromString != nil)
        #expect(model.requestKey.fromString == model.requestKey.toString)
    }

    @Test("comedian and club discovery models send selected filters and sort")
    func primitiveDiscoveryModelsSendSelectedFiltersAndSort() async {
        let transport = StubClientTransport { _, _, _, operationID in
            switch operationID {
            case "searchComedians":
                return testJSONResponse(#"{"data":[],"total":0,"filters":[],"homeCityFilters":[]}"#)
            case "searchClubs":
                return testJSONResponse(#"{"data":[],"total":0,"filters":[]}"#)
            default:
                Issue.record("Unexpected operation \(operationID)")
                return testJSONResponse(#"{"error":"unexpected"}"#, status: .internalServerError)
            }
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        let comedians = ComediansDiscoveryModel()
        comedians.selectedFilterSlugs = ["podcast", "stand-up"]
        comedians.sort = .alphabetical
        await comedians.reload(apiClient: client, favorites: ComedianFavoriteStore())

        let clubs = makeClubsDiscoveryModel()
        clubs.selectedFilterSlugs = ["independent", "downtown"]
        clubs.sort = .leastPopular
        await clubs.reload(apiClient: client)

        let requests = transport.capturedRequests
        let comedianPath = requests.first(where: { $0.operationID == "searchComedians" })?.path
        let clubPath = requests.first(where: { $0.operationID == "searchClubs" })?.path
        let comedianFilters = queryValue("filters", from: comedianPath)
        let clubFilters = queryValue("filters", from: clubPath)
        let comedianSort = queryValue("sort", from: comedianPath)
        let clubSort = queryValue("sort", from: clubPath)
        #expect(comedianFilters == "podcast,stand-up")
        #expect(clubFilters == "downtown,independent")
        #expect(comedianSort == "name_asc")
        #expect(clubSort == "popularity_asc")
    }

    @Test("comedian discovery threads the homeCity token and surfaces homeCityFilters options")
    func comedianDiscoverySendsHomeCityTokenAndStoresOptions() async {
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchComedians")
            return testJSONResponse(
                #"""
                {
                  "data": [],
                  "total": 0,
                  "filters": [],
                  "homeCityFilters": [
                    { "value": "Chicago|IL", "label": "Chicago, IL", "count": 7 },
                    { "value": "Austin|TX", "label": "Austin, TX", "count": 3 }
                  ]
                }
                """#
            )
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        let comedians = ComediansDiscoveryModel()
        comedians.homeCity = "Chicago|IL"
        await comedians.reload(apiClient: client, favorites: ComedianFavoriteStore())

        // Applying a home-city re-queries with the token.
        let comedianPath = transport.capturedRequests.first(where: { $0.operationID == "searchComedians" })?.path
        #expect(queryValue("homeCity", from: comedianPath) == "Chicago|IL")

        // The control's options come from the response's homeCityFilters.
        guard case .success(let page) = comedians.phase else {
            Issue.record("Expected comedian discovery to retain a success page")
            return
        }
        #expect(page.homeCityFilters.map(\.value) == ["Chicago|IL", "Austin|TX"])
        #expect(page.homeCityFilters.map(\.count) == [7, 3])
    }

    @Test("comedian search decode failures are not shown as connection failures")
    func comedianSearchDecodeFailuresClassifyAsDataIssues() async {
        let model = ComediansDiscoveryModel()
        model.searchText = "bad payload"
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            transport: MalformedSearchTransport()
        )

        await model.reload(apiClient: client, favorites: ComedianFavoriteStore())

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected comedian search to surface a failure phase")
            return
        }

        #expect(failure.defaultTitle == "Data issue")
    }

    @Test("club search decode failures are not shown as connection failures")
    func clubSearchDecodeFailuresClassifyAsDataIssues() async {
        let model = makeClubsDiscoveryModel()
        model.searchText = "bad payload"
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            transport: MalformedSearchTransport()
        )

        await model.reload(apiClient: client)

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected club search to surface a failure phase")
            return
        }

        #expect(failure.defaultTitle == "Data issue")
    }

    @Test("failure messages include status codes and classify by case")
    func loadFailureDisplay() {
        #expect(LoadFailure.network("No signal").message == "No signal")
        #expect(LoadFailure.network("No signal").defaultTitle == "No connection")

        #expect(LoadFailure.decoding("Unreadable").message == "Unreadable")
        #expect(LoadFailure.decoding("Unreadable").defaultTitle == "Data issue")

        #expect(LoadFailure.unauthorized("Session expired").message == "Session expired (HTTP 401)")
        #expect(LoadFailure.unauthorized("Session expired").defaultTitle == "Sign in required")

        #expect(LoadFailure.badParams("Bad date").message == "Bad date (HTTP 400)")

        let server = LoadFailure.serverError(status: 503, message: "Upstream down")
        #expect(server.message == "Upstream down (HTTP 503)")
        #expect(server.defaultTitle == "Server hiccup")

        let serverNoMessage = LoadFailure.serverError(status: 500, message: nil)
        #expect(serverNoMessage.message.contains("HTTP 500"))

        #expect(LoadFailure.unexpected(status: 429, message: "Rate limited").message == "Rate limited (HTTP 429)")
        #expect(LoadFailure.unexpected(status: 0, message: "Local-only note").message == "Local-only note")

        let limited = LoadFailure.rateLimited(retryAfter: nil, message: "Slowing things down.")
        #expect(limited.message == "Slowing things down. Please try again in a moment. (HTTP 429)")
        #expect(limited.defaultTitle == "Too many requests")

        let limitedWithRetry = LoadFailure.rateLimited(retryAfter: 12, message: nil)
        #expect(limitedWithRetry.message == "LaughTrack is busy right now. Please try again in 12 seconds. (HTTP 429)")

        let limitedSingleSecond = LoadFailure.rateLimited(retryAfter: 1, message: nil)
        #expect(limitedSingleSecond.message.contains("1 second."))
    }

    @Test("recovery action routes unauthorized to signIn, everything else to retry")
    func recoveryActionRouting() {
        #expect(LoadFailure.unauthorized("x").recoveryAction == .signIn)
        #expect(LoadFailure.network("y").recoveryAction == .retry)
        #expect(LoadFailure.decoding("y").recoveryAction == .retry)
        #expect(LoadFailure.badParams("z").recoveryAction == .retry)
        #expect(LoadFailure.rateLimited(retryAfter: nil, message: nil).recoveryAction == .retry)
        #expect(LoadFailure.serverError(status: 500, message: nil).recoveryAction == .retry)
        #expect(LoadFailure.unexpected(status: 418, message: nil).recoveryAction == .retry)
    }

    @Test("cancelled reloads do not overwrite phase with failure")
    func cancelledReloadKeepsPhase() async {
        let model = EntitySearchModel<String, Int>()

        let task = Task {
            await model.reload(query: "shows") { _, _ in
                try? await Task.sleep(for: .milliseconds(50))
                return .failure(.network("Simulated cancellation"))
            }
        }
        task.cancel()
        await task.value

        if case .failure = model.phase {
            Issue.record("Cancelled reload must not surface a failure phase")
        }
    }

    @Test("undocumented statuses classify into the right case")
    func classifyUndocumentedMaps() {
        if case .unauthorized = classifyUndocumented(status: 401, context: "shows") {} else {
            Issue.record("401 must map to .unauthorized")
        }
        if case .badParams = classifyUndocumented(status: 400, context: "shows") {} else {
            Issue.record("400 must map to .badParams")
        }
        if case .serverError(let status, _) = classifyUndocumented(status: 502, context: "shows") {
            #expect(status == 502)
        } else {
            Issue.record("5xx must map to .serverError")
        }
        if case .rateLimited = classifyUndocumented(status: 429, context: "shows") {} else {
            Issue.record("429 must map to .rateLimited")
        }
        if case .unexpected(let status, _) = classifyUndocumented(status: 418, context: "shows") {
            #expect(status == 418)
        } else {
            Issue.record("Other statuses must map to .unexpected")
        }
    }

    @Test("show detail surfaces a non-nil retryAfter from the 429 Retry-After header")
    func showDetailRateLimitedExtractsRetryAfterFromHeader() async {
        let transport = StubRateLimitedShowTransport(retryAfter: 12)
        let client = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let model = ShowDetailModel(showID: 301)
        await model.loadIfNeeded(apiClient: client, favorites: ComedianFavoriteStore())

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected ShowDetailModel to surface a failure phase for 429")
            return
        }
        guard case .rateLimited(let retryAfter, _) = failure else {
            Issue.record("Expected .rateLimited failure, got \(failure)")
            return
        }
        #expect(retryAfter == 12)
        #expect(failure.message.contains("Please try again in 12 seconds."))
    }

    @Test("detail model only performs its first automatic load once")
    func detailModelOnlyLoadsOnceWhenIdle() async {
        let model = EntityDetailModel<Int>()
        var callCount = 0

        await model.loadIfNeeded {
            callCount += 1
            return .success(42)
        }

        await model.loadIfNeeded {
            callCount += 1
            return .success(99)
        }

        #expect(callCount == 1)

        switch model.phase {
        case .success(let value):
            #expect(value == 42)
        default:
            Issue.record("Expected detail model to hold onto its first loaded value")
        }
    }
}

private struct RawShowRailTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "getHomeFeed":
            return jsonResponse(try homeFeedJSON())
        case "searchShows":
            return jsonResponse(
                """
                {
                  "data": [
                    {
                      "id": 200,
                      "clubId": 123,
                      "date": "2026-05-27T01:30:00.000Z",
                      "name": "Sold Out Search Show",
                      "clubName": "Flappers Comedy Club And Restaurant Burbank",
                      "imageUrl": "/placeholders/club-placeholder.svg",
                      "soldOut": true,
                      "lineup": [],
                      "tickets": []
                    },
                    {
                      "id": 201,
                      "clubId": 123,
                      "date": "2026-05-27T02:30:00.000Z",
                      "name": "Search Show",
                      "clubName": "Flappers Comedy Club And Restaurant Burbank",
                      "imageUrl": "/placeholders/club-placeholder.svg",
                      "soldOut": false,
                      "lineup": [],
                      "tickets": []
                    }
                  ],
                  "total": 2,
                  "filters": [],
                  "zipCapTriggered": false
                }
                """
            )
        default:
            return jsonResponse(#"{"error":"unexpected operation"}"#, status: .internalServerError)
        }
    }

    private func jsonResponse(
        _ body: String,
        status: HTTPResponse.Status = .ok
    ) -> (HTTPResponse, HTTPBody?) {
        (
            HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
            HTTPBody(body)
        )
    }

    // Derive the response body from the struct fixture so adding a non-optional
    // field to HomeFeed can't silently break decoding here (TASK-2307, TASK-2442).
    private func homeFeedJSON() throws -> String {
        let feed = Components.Schemas.HomeFeed(
            hero: .init(
                zipCode: "10012",
                city: "New York",
                state: "NY",
                shows: []
            ),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [
                .init(
                    id: 100,
                    clubId: 301,
                    clubName: "New York Comedy Club",
                    date: Date().addingTimeInterval(30 * 60),
                    tickets: [
                        .init(
                            price: 9.0,
                            purchaseUrl: "https://example.com/sold-out",
                            soldOut: true,
                            _type: "General Admission"
                        )
                    ],
                    name: "Sold Out Tonight Show",
                    lineup: [],
                    imageUrl: "https://example.com/sold-out-show.png",
                    soldOut: true
                ),
                .init(
                    id: 101,
                    clubId: 301,
                    clubName: "New York Comedy Club",
                    date: Date().addingTimeInterval(60 * 60),
                    tickets: [
                        .init(
                            price: 9.0,
                            purchaseUrl: "https://example.com/tickets",
                            soldOut: false,
                            _type: "General Admission"
                        )
                    ],
                    name: "Tonight Show",
                    lineup: [],
                    imageUrl: "https://example.com/show.png"
                )
            ],
            moreNearYou: [],
            trendingThisWeek: [],
            followedComedianShows: [],
            trendingPodcasts: [],
            popularClubs: []
        )
        let envelope = Components.Schemas.HomeFeedResponse(data: feed)
        let data = try APIMockEncoder.make().encode(envelope)
        return String(decoding: data, as: UTF8.self)
    }
}

private struct MalformedSearchTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "searchComedians":
            return jsonResponse(
                """
                {
                  "data": [
                    {
                      "id": 301,
                      "uuid": "comic-bad-payload",
                      "name": "Bad Payload Comic",
                      "imageUrl": "https://example.com/comic.png",
                      "social_data": null,
                      "show_count": 4,
                      "isFavorite": false
                    }
                  ],
                  "total": 1,
                  "filters": []
                }
                """
            )
        case "searchClubs":
            return jsonResponse(
                """
                {
                  "data": [
                    {
                      "id": 401,
                      "name": "Bad Payload Club",
                      "active_comedian_count": 3
                    }
                  ],
                  "total": 1,
                  "filters": []
                }
                """
            )
        default:
            return jsonResponse(#"{"error":"unexpected operation"}"#, status: .internalServerError)
        }
    }

    private func jsonResponse(
        _ body: String,
        status: HTTPResponse.Status = .ok
    ) -> (HTTPResponse, HTTPBody?) {
        (
            HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
            HTTPBody(body)
        )
    }
}

private func testJSONResponse(
    _ body: String,
    status: HTTPResponse.Status = .ok
) -> (HTTPResponse, HTTPBody?) {
    (
        HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
        HTTPBody(body)
    )
}

private func queryValue(_ name: String, from path: String?) -> String? {
    guard let path, let components = URLComponents(string: "https://test.example.com\(path)") else { return nil }
    return components.queryItems?.first(where: { $0.name == name })?.value
}

@MainActor
private func makeClubsDiscoveryModel() -> ClubsDiscoveryModel {
    ClubsDiscoveryModel(
        nearbyLocationController: NearbyLocationController(
            store: NearbyPreferenceStore(),
            resolver: StubNearbyLocationResolver(),
            zipLocationResolver: StubZipLocationResolver()
        )
    )
}

private func makeTrendingComedians(
    photoCount: Int,
    includesNoPhoto: Bool
) -> [Components.Schemas.ComedianListItem] {
    let photoBacked = (1...photoCount).map { index in
        Components.Schemas.ComedianListItem(
            id: 1000 + index,
            uuid: "trending-comedian-\(index)",
            name: "Comic \(index)",
            imageUrl: "https://example.com/comic-\(index).jpg",
            socialData: .init(
                id: 2000 + index,
                instagramAccount: nil,
                instagramFollowers: nil,
                tiktokAccount: nil,
                tiktokFollowers: nil,
                youtubeAccount: nil,
                youtubeFollowers: nil,
                website: nil,
                popularity: nil,
                linktree: nil
            ),
            showCount: 11 - index
        )
    }

    guard includesNoPhoto else { return photoBacked }

    return photoBacked + [
        .init(
            id: 2001,
            uuid: "trending-comedian-no-photo",
            name: "No Photo Comic",
            imageUrl: "",
            socialData: .init(
                id: 3001,
                instagramAccount: nil,
                instagramFollowers: nil,
                tiktokAccount: nil,
                tiktokFollowers: nil,
                youtubeAccount: nil,
                youtubeFollowers: nil,
                website: nil,
                popularity: nil,
                linktree: nil
            ),
            showCount: 3
        )
    ]
}

private func makeShow(
    id: Int,
    lineup: [Components.Schemas.ComedianLineup]
) -> Components.Schemas.Show {
    .init(
        id: id,
        clubId: 202,
        clubName: "The Stand",
        date: Date().addingTimeInterval(60 * 60 * 24),
        tickets: [],
        name: "Favorite comic showcase",
        socialData: nil,
        lineup: lineup,
        description: "A test show.",
        address: "116 E 16th St, New York, NY",
        room: "Main Room",
        imageUrl: "https://example.com/show.png",
        soldOut: false,
        distanceMiles: nil
    )
}

private struct StubRateLimitedShowTransport: ClientTransport {
    let retryAfter: Int

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let response = HTTPResponse(
            status: .tooManyRequests,
            headerFields: [
                .contentType: "application/json",
                .retryAfter: String(retryAfter),
            ]
        )
        return (response, HTTPBody(#"{"error":"slow down"}"#))
    }
}

@Suite("Search refresh continuity")
@MainActor
struct SearchRefreshContinuityTests {
    @Test("previous results remain visible through debounce and a slow response")
    func preservesResultsThroughDebounceAndRefresh() async throws {
        let model = await seededModel()
        let gate = SearchRefreshResponseGate()
        var observedRefreshStart = false
        let observation = model.$isRefreshing.sink { refreshing in
            guard refreshing else { return }
            observedRefreshStart = true
            #expect(gate.requestCount == 0)
            #expect(items(model) == [1, 2])
        }
        defer { observation.cancel() }
        let refresh = Task {
            await model.reload(query: "new", shouldDebounce: true) { _, _ in await gate.fetch() }
        }
        try await waitUntil { gate.requestCount == 1 }
        #expect(observedRefreshStart)
        #expect(model.resultsState(for: "new") == .updating)
        #expect(items(model) == [1, 2])
        gate.resolve(0, items: [3])
        await refresh.value
        #expect(items(model) == [3])
        #expect(!model.isRefreshing)
        #expect(model.resultsState(for: "new").isConfirmed)
    }

    @Test("older responses cannot settle a newer query or clear its updating state")
    func ignoresOutOfOrderResponses() async throws {
        let model = await seededModel()
        let gate = SearchRefreshResponseGate()
        let old = Task { await model.reload(query: "R") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        let latest = Task { await model.reload(query: "Ray") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 2 }
        gate.resolve(0, items: [99])
        await old.value
        #expect(items(model) == [1, 2])
        #expect(model.isRefreshing)
        #expect(model.resultsState(for: "Ray") == .updating)
        gate.resolve(1, items: [3])
        await latest.value
        #expect(items(model) == [3])
        #expect(model.resultsState(for: "Ray").isConfirmed)
    }

    @Test("canceled debounce retains content without claiming the new query matched")
    func canceledDebounceRetainsUnconfirmedContent() async throws {
        let model = await seededModel()
        var refresh: Task<Void, Never>?
        let observation = model.$isRefreshing.sink { refreshing in
            if refreshing { refresh?.cancel() }
        }
        defer { observation.cancel() }
        let task = Task {
            await model.reload(query: "new", shouldDebounce: true) { _, _ in
                Issue.record("Canceled debounce must not fetch")
                return .success(.init(items: [99], total: 1))
            }
        }
        refresh = task
        await task.value
        #expect(items(model) == [1, 2])
        #expect(!model.isRefreshing)
        #expect(model.refreshFailure == nil)
        #expect(model.resultsState(for: "new") == .interrupted)
        #expect(model.resultsState(for: "original").isConfirmed)
    }

    @Test("canceled transport responses cannot overwrite a retry of the same query")
    func canceledInFlightResponseCannotOverwriteRetry() async throws {
        let model = await seededModel()
        let gate = SearchRefreshResponseGate()
        let canceled = Task { await model.reload(query: "new") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        canceled.cancel()
        let retry = Task { await model.reload(query: "new") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 2 }
        gate.resolve(0, items: [99])
        await canceled.value
        #expect(model.isRefreshing)
        #expect(items(model) == [1, 2])
        gate.resolve(1, items: [3])
        await retry.value
        #expect(items(model) == [3])
        #expect(model.resultsState(for: "new").isConfirmed)
    }

    @Test("clearing back to cached query invalidates a competing response and preserves pages")
    func returningToCachedQueryInvalidatesCompetingResponse() async throws {
        let model = await seededModel(query: "")
        await model.loadMore(query: "") { _, _ in .success(.init(items: [3, 4], total: 4)) }
        let gate = SearchRefreshResponseGate()
        let search = Task { await model.reload(query: "Ray") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        await model.reload(query: "", cacheTTL: 60) { _, _ in
            Issue.record("Fresh cached query must retain its accumulated pages")
            return .success(.init(items: [99], total: 1))
        }
        #expect(items(model) == [1, 2, 3, 4])
        #expect(model.resultsState(for: "").isConfirmed)
        #expect(!model.isRefreshing)
        gate.resolve(0, items: [99])
        await search.value
        #expect(items(model) == [1, 2, 3, 4])
        #expect(model.resultsState(for: "").isConfirmed)
    }

    @Test("initial load, initial cancellation, failure, and recovery remain distinct")
    func initialLoadingFailureAndRecovery() async throws {
        let model = EntitySearchModel<String, Int>()
        let gate = SearchRefreshResponseGate()
        let initial = Task { await model.reload(query: "first") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        if case .loading = model.phase {} else { Issue.record("Initial request needs loading phase") }
        #expect(!model.isRefreshing)
        initial.cancel()
        gate.resolve(0, items: [99])
        await initial.value
        if case .idle = model.phase {} else { Issue.record("Canceled initial request must return to idle") }
        await model.reload(query: "first") { _, _ in .failure(.network("Offline")) }
        if case .failure(let error) = model.phase {
            #expect(error == .network("Offline"))
        } else { Issue.record("Initial offline request needs failure phase") }
        await model.reload(query: "first") { _, _ in .success(.init(items: [1], total: 1)) }
        #expect(items(model) == [1])
        #expect(model.resultsState(for: "first").isConfirmed)
    }

    @Test("refresh failure labels retained results and permits recovery without pagination")
    func refreshFailureRetainsResultsAndRetries() async {
        let model = await seededModel()
        await model.reload(query: "new") { _, _ in .failure(.network("Offline")) }
        #expect(items(model) == [1, 2])
        #expect(model.refreshFailure == .network("Offline"))
        #expect(model.resultsState(for: "new") == .failed(.network("Offline")))
        #expect(!model.isRefreshing)
        await model.loadMore(query: "new") { _, _ in
            Issue.record("Unconfirmed results must not paginate")
            return .success(.init(items: [99], total: 4))
        }
        await model.loadPage(1, query: "new") { _, _ in
            Issue.record("Unconfirmed results must not navigate pages")
            return .success(.init(items: [99], total: 4))
        }
        await model.reload(query: "new") { _, _ in .success(.init(items: [3], total: 1)) }
        #expect(items(model) == [3])
        #expect(model.refreshFailure == nil)
        #expect(model.resultsState(for: "new").isConfirmed)
    }

    @Test("obsolete pagination cannot append to new results or stop a newer page spinner")
    func stalePaginationDoesNotAppendOrClearNewSpinner() async throws {
        let model = await seededModel()
        let gate = SearchRefreshResponseGate()
        let oldPage = Task { await model.loadMore(query: "original") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        await model.reload(query: "new") { _, _ in .success(.init(items: [3], total: 2)) }
        let newPage = Task { await model.loadMore(query: "new") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 2 }
        #expect(model.isLoadingMore)
        gate.resolve(0, items: [99], total: 4)
        await oldPage.value
        #expect(items(model) == [3])
        #expect(model.isLoadingMore)
        gate.resolve(1, items: [4], total: 2)
        await newPage.value
        #expect(items(model) == [3, 4])
        #expect(!model.isLoadingMore)
    }

    @Test("pagination failures keep confirmed results and can recover")
    func paginationFailureAndRecovery() async {
        let model = await seededModel()
        await model.loadMore(query: "original") { _, _ in .failure(.network("Offline")) }
        #expect(items(model) == [1, 2])
        #expect(model.paginationFailure == .network("Offline"))
        #expect(model.refreshFailure == nil)
        #expect(model.resultsState(for: "original").isConfirmed)
        await model.loadMore(query: "original") { page, _ in
            #expect(page == 1)
            return .success(.init(items: [3, 4], total: 4))
        }
        #expect(items(model) == [1, 2, 3, 4])
        #expect(model.paginationFailure == nil)
    }

    @Test("previous empty results are retained but not confirmed for a pending query")
    func previousEmptyResultsRemainUnconfirmedDuringRefresh() async throws {
        let model = EntitySearchModel<String, Int>()
        await model.reload(query: "missing") { _, _ in .success(.init(items: [], total: 0)) }
        let gate = SearchRefreshResponseGate()
        let refresh = Task { await model.reload(query: "new") { _, _ in await gate.fetch() } }
        try await waitUntil { gate.requestCount == 1 }
        #expect(items(model) == [])
        #expect(model.isRefreshing)
        #expect(!model.resultsState(for: "new").isConfirmed)
        gate.resolve(0, items: [1])
        await refresh.value
        #expect(items(model) == [1])
        #expect(model.resultsState(for: "new").isConfirmed)
    }

    @Test("fresh same-query return keeps accumulated results and expired cache refreshes them")
    func sameQueryReturnAndCacheExpiry() async throws {
        let model = await seededModel()
        await model.loadMore(query: "original") { _, _ in .success(.init(items: [3, 4], total: 4)) }
        await model.reload(query: "original", cacheTTL: 60) { _, _ in
            Issue.record("Returning from detail must not replace fresh accumulated results")
            return .success(.init(items: [], total: 0))
        }
        #expect(items(model) == [1, 2, 3, 4])
        let gate = SearchRefreshResponseGate()
        let refresh = Task {
            await model.reload(query: "original", cacheTTL: 0) { _, _ in await gate.fetch() }
        }
        try await waitUntil { gate.requestCount == 1 }
        #expect(items(model) == [1, 2, 3, 4])
        #expect(model.isRefreshing)
        gate.resolve(0, items: [5])
        await refresh.value
        #expect(items(model) == [5])
        #expect(model.resultsState(for: "original").isConfirmed)
    }

    @Test("category switching restores each draft while changed queries remain unconfirmed")
    func categorySwitchingPreservesModelsAndQueryHonesty() async {
        let root = SearchRootModel()
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "category-refresh")
        let shows = ShowsListModel(nearbyLocationController: LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store))
        let comedians = ComediansDiscoveryModel()
        let clubs = makeClubsDiscoveryModel()
        let podcasts = PodcastSearchModel(fetcher: APIPodcastSearchFetcher(apiClient: LaughTrackHostedViewTestSupport.makeClient()))
        func applyQuery() {
            root.applyQuery(showsModel: shows, comediansModel: comedians, clubsModel: clubs, podcastsModel: podcasts)
        }
        let first = PodcastSearchResult(id: "podcast-1", title: "Comedy One", subtitle: nil, href: "/podcast/one", imageUrl: nil)
        let second = PodcastSearchResult(id: "podcast-2", title: "Comedy Two", subtitle: nil, href: "/podcast/two", imageUrl: nil)
        root.activePivot = .podcasts
        root.query = "Comedy"
        applyQuery()
        await podcasts.reload(query: podcasts.requestKey) { _, _ in .success(.init(items: [first], total: 2)) }
        await podcasts.loadMore(query: podcasts.requestKey) { _, _ in .success(.init(items: [second], total: 2)) }
        root.activePivot = .clubs
        applyQuery()
        await clubs.reload(query: clubs.requestKey) { _, _ in .success(.init(items: [], total: 0)) }
        #expect(clubs.resultsState(for: clubs.requestKey).isConfirmed)
        root.activePivot = .podcasts
        applyQuery()
        await podcasts.reload(query: podcasts.requestKey, cacheTTL: 60) { _, _ in
            Issue.record("Same-query category return must retain loaded pages")
            return .success(.init(items: [], total: 0))
        }
        #expect(podcasts.currentItems == [first, second])
        #expect(podcasts.resultsState(for: podcasts.requestKey).isConfirmed)
        root.activePivot = .clubs
        root.query = "Ray"
        applyQuery()
        #expect(clubs.searchText == "Ray")
        #expect(podcasts.searchText == "Comedy")
        root.activePivot = .podcasts
        applyQuery()
        #expect(root.query == "Comedy")
        #expect(podcasts.searchText == "Comedy")
        #expect(podcasts.resultsState(for: podcasts.requestKey).isConfirmed)
        root.query = "Ray"
        applyQuery()
        #expect(podcasts.searchText == "Ray")
        #expect(podcasts.currentItems == [first, second])
        #expect(!podcasts.resultsState(for: podcasts.requestKey).isConfirmed)
    }

    private func seededModel(query: String = "original") async -> EntitySearchModel<String, Int> {
        let model = EntitySearchModel<String, Int>()
        await model.reload(query: query) { _, _ in .success(.init(items: [1, 2], total: 4)) }
        return model
    }

    private func items(_ model: EntitySearchModel<String, Int>) -> [Int]? {
        guard case .success(let page) = model.phase else {
            Issue.record("Expected visible successful results")
            return nil
        }
        return page.items
    }

    private func waitUntil(_ condition: () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(3)
        while !condition(), Date() < deadline {
            try await Task.sleep(for: .milliseconds(5))
        }
        try #require(condition(), "Timed out waiting for controlled request state")
    }
}

/// Deliberately ignores cancellation, like a transport that has already produced
/// a response. Tests explicitly determine completion order without timed sleeps.
@MainActor
private final class SearchRefreshResponseGate {
    typealias Response = Result<DiscoverySearchResponse<Int>, LoadFailure>
    private var continuations: [Int: CheckedContinuation<Response, Never>] = [:]
    private(set) var requestCount = 0

    func fetch() async -> Response {
        await withCheckedContinuation { continuation in
            continuations[requestCount] = continuation
            requestCount += 1
        }
    }

    func resolve(_ request: Int, items: [Int], total: Int? = nil) {
        let continuation = continuations.removeValue(forKey: request)
        #expect(continuation != nil)
        continuation?.resume(returning: .success(.init(items: items, total: total ?? items.count)))
    }
}

@Suite("Entity detail cancellation", .timeLimit(.minutes(1)))
@MainActor
struct EntityDetailCancellationTests {
    @Test("cancelled initial loads become idle and can load again", arguments: [false, true])
    func initialCancellationRecovers(networkFailure: Bool) async throws {
        let model = EntityDetailModel<Int>()
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let initial = Task { await model.loadIfNeeded { await gate.fetch() } }
        try await gate.waitForRequests(1)
        initial.cancel()
        gate.resolve(0, networkFailure
            ? .failure(classifyDetailFetchError(URLError(.cancelled), context: "show"))
            : .success(99))
        await initial.value
        if case .idle = model.phase {} else { Issue.record("Cancellation must leave a loadable idle state") }
        await model.loadIfNeeded { .success(42) }
        #expect(value(model) == 42)
    }

    @Test("returning before cancelled transport finishes starts a fresh load")
    func returnBeforeOldTransportFinishes() async throws {
        let model = EntityDetailModel<Int>()
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let initial = Task { await model.loadIfNeeded { await gate.fetch() } }
        try await gate.waitForRequests(1)
        initial.cancel()
        await model.loadIfNeeded { .success(42) }
        #expect(value(model) == 42)
        gate.resolve(0, .success(99))
        await initial.value
        #expect(value(model) == 42)
    }

    @Test("obsolete cancellation cannot clear a newer loading phase")
    func obsoleteCancellationPreservesNewLoading() async throws {
        let model = EntityDetailModel<Int>()
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let initial = Task { await model.reload { await gate.fetch() } }
        try await gate.waitForRequests(1)
        initial.cancel()
        let newer = Task { await model.reload { await gate.fetch() } }
        try await gate.waitForRequests(2)
        gate.resolve(0, .failure(.network("Cancelled transport")))
        await initial.value
        if case .loading = model.phase {} else { Issue.record("Old cancellation must not clear the active request") }
        gate.resolve(1, .success(42))
        await newer.value
        #expect(value(model) == 42)
    }

    @Test("superseded noncooperative requests cannot replace newer content", arguments: [false, true])
    func supersededResponseCannotReplaceContent(failure: Bool) async throws {
        let model = EntityDetailModel<Int>()
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let initial = Task { await model.reload { await gate.fetch() } }
        try await gate.waitForRequests(1)
        await model.reload { .success(42) }
        gate.resolve(0, failure ? .failure(.network("Obsolete failure")) : .success(99))
        await initial.value
        #expect(value(model) == 42)
    }

    @Test("genuine failures remain visible and explicit retry succeeds")
    func failureCanBeRetried() async {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .failure(.network("Offline")) }
        if case .failure(let failure) = model.phase {
            #expect(failure == .network("Offline"))
            #expect(failure.recoveryAction == .retry)
        } else { Issue.record("A real failure must remain visible") }
        await model.reload { .success(42) }
        #expect(value(model) == 42)
    }

    @Test("an already-cancelled caller cannot replace loaded content or start transport")
    func cancelledCallerDoesNotStart() async {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .success(42) }
        let cancelled = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            await model.reload {
                Issue.record("Already-cancelled caller must not begin a request")
                return .success(99)
            }
        }
        await cancelled.value
        #expect(value(model) == 42)
    }

    #if canImport(UIKit)
    @Test("a retained detail recovers after SwiftUI removes and reinserts its loading view")
    func retainedViewReappearsBeforeCancelledTransportFinishes() async throws {
        let model = EntityDetailModel<Int>()
        let gate = DetailCancellationResponseGate()
        let visibility = DetailCancellationVisibility()
        let host = HostedView(DetailCancellationLifecycleView(model: model, gate: gate, visibility: visibility))
        defer { gate.resolveAll(); visibility.isVisible = false }
        await host.settle()
        try await gate.waitForRequests(1)
        visibility.isVisible = false
        await host.settle()
        visibility.isVisible = true
        await host.settle()
        try await gate.waitForRequests(2)
        gate.resolve(1, .success(42))
        await host.settle()
        #expect(value(model) == 42)
        gate.resolve(0, .success(99))
        await host.settle()
        #expect(value(model) == 42)
    }
    #endif

    private func value(_ model: EntityDetailModel<Int>) -> Int? {
        guard case .success(let value) = model.phase else { return nil }
        return value
    }
}

/// The transport deliberately ignores cancellation so tests control completion
/// order, including returning to a retained view before an old response arrives.
@MainActor
private final class DetailCancellationResponseGate {
    typealias Response = Result<Int, LoadFailure>
    private var continuations: [Int: CheckedContinuation<Response, Never>] = [:]
    private(set) var requestCount = 0

    func fetch() async -> Response {
        await withCheckedContinuation { continuation in
            continuations[requestCount] = continuation
            requestCount += 1
        }
    }

    func waitForRequests(_ count: Int) async throws {
        let deadline = Date().addingTimeInterval(3)
        while requestCount < count, Date() < deadline { await Task.yield() }
        try #require(requestCount >= count, "Expected controlled detail request to start")
    }

    func resolve(_ index: Int, _ result: Response) {
        let continuation = continuations.removeValue(forKey: index)
        #expect(continuation != nil)
        continuation?.resume(returning: result)
    }

    func resolveAll() {
        let pending = Array(continuations.values)
        continuations.removeAll()
        for continuation in pending { continuation.resume(returning: .failure(.network("Test cleanup"))) }
    }
}

#if canImport(UIKit)
@MainActor
private final class DetailCancellationVisibility: ObservableObject {
    @Published var isVisible = true
}

private struct DetailCancellationLifecycleView: View {
    @ObservedObject var model: EntityDetailModel<Int>
    let gate: DetailCancellationResponseGate
    @ObservedObject var visibility: DetailCancellationVisibility

    var body: some View {
        Group {
            if visibility.isVisible {
                Text("Detail")
                    .task { await model.loadIfNeeded { await gate.fetch() } }
            }
        }
    }
}
#endif

@Suite("Detail freshness and refresh", .timeLimit(.minutes(1)))
@MainActor
struct DetailRefreshTests {
    @Test("successful detail stays fresh for a bounded interval and refreshes on expiry")
    func freshnessUsesLastSuccessfulResponse() async {
        var now = Date(timeIntervalSince1970: 1_000)
        let model = EntityDetailModel<Int>(now: { now })
        var calls = 0
        await model.loadIfNeeded(freshness: 60) { calls += 1; return .success(calls) }
        now = now.addingTimeInterval(59)
        await model.loadIfNeeded(freshness: 60) { calls += 1; return .success(calls) }
        #expect(calls == 1)
        now = now.addingTimeInterval(1)
        await model.loadIfNeeded(freshness: 60) { calls += 1; return .success(calls) }
        #expect(calls == 2)
        #expect(value(model) == 2)
    }

    @Test("refresh keeps content visible and coalesces simultaneous callers")
    func refreshPreservesContentAndCoalesces() async throws {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .success(1) }
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let first = Task { await model.refresh { await gate.fetch() } }
        try await gate.waitForRequests(1)
        #expect(model.isRefreshing)
        #expect(value(model) == 1)
        var secondEntered = false
        let second = Task {
            secondEntered = true
            await model.refresh {
                Issue.record("A simultaneous refresh must reuse the active request")
                return .success(99)
            }
        }
        while !secondEntered { await Task.yield() }
        gate.resolve(0, .success(2))
        await first.value
        await second.value
        #expect(value(model) == 2)
        #expect(!model.isRefreshing)
        #expect(model.refreshFailure == nil)
        #expect(gate.requestCount == 1)
    }

    @Test("failed revalidation retains data, reports failure and remains eligible for retry")
    func failurePreservesContentAndDoesNotAdvanceFreshness() async {
        var now = Date(timeIntervalSince1970: 1_000)
        let model = EntityDetailModel<Int>(now: { now })
        await model.loadIfNeeded(freshness: 60) { .success(1) }
        now = now.addingTimeInterval(60)
        await model.loadIfNeeded(freshness: 60) { .failure(.network("Offline")) }
        #expect(value(model) == 1)
        #expect(model.refreshFailure == .network("Offline"))
        #expect(!model.isRefreshing)
        await model.loadIfNeeded(freshness: 60) { .success(2) }
        #expect(value(model) == 2)
        #expect(model.refreshFailure == nil)
    }

    @Test("cancelled refresh can be retried before old transport unwinds without blanking")
    func cancelledRefreshCanRetryImmediately() async throws {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .success(1) }
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let first = Task { await model.refresh { await gate.fetch() } }
        try await gate.waitForRequests(1)
        first.cancel()
        #expect(value(model) == 1)
        await model.refresh { .success(2) }
        gate.resolve(0, .failure(.network("Obsolete failure")))
        await first.value
        #expect(value(model) == 2)
        #expect(model.refreshFailure == nil)
        #expect(!model.isRefreshing)
    }

    @Test("explicit reload supersedes an old refresh while retaining loaded content")
    func reloadOwnsNewestResponse() async throws {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .success(1) }
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let old = Task { await model.refresh { await gate.fetch() } }
        try await gate.waitForRequests(1)
        let newer = Task { await model.reload { await gate.fetch() } }
        try await gate.waitForRequests(2)
        #expect(value(model) == 1)
        gate.resolve(0, .success(99))
        await old.value
        #expect(model.isRefreshing)
        #expect(value(model) == 1)
        gate.resolve(1, .success(2))
        await newer.value
        #expect(value(model) == 2)
        #expect(!model.isRefreshing)
    }

    @Test("cached show appears immediately then revalidates changed ticket availability")
    func cachedShowRevalidatesWithoutSkeleton() async throws {
        let cached = DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
        var updated = cached
        updated.data.soldOut = !(cached.data.soldOut ?? false)
        let body = try APIMockEncoder.make().encode(updated)
        let cache = DataCache<LaughTrackCacheKey>()
        await MainPageCache.set(cached, forKey: .show(id: "301"), in: cache, persistentCache: nil)
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "getShow")
            _ = await gate.fetch()
            return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(body))
        }
        let client = Client(serverURL: URL(string: "https://test.example.com")!, configuration: .laughTrack, transport: transport)
        let model = ShowDetailModel(showID: 301)
        let load = Task { await model.loadIfNeeded(apiClient: client, favorites: ComedianFavoriteStore(), cache: cache) }
        try await gate.waitForRequests(1)
        guard case .success(let visible) = model.phase else {
            Issue.record("Cached show should remain visible during revalidation")
            return
        }
        #expect(visible.data.soldOut == cached.data.soldOut)
        #expect(model.isRefreshing)
        gate.resolve(0, .success(0))
        await load.value
        guard case .success(let refreshed) = model.phase else {
            Issue.record("Expected updated show after revalidation")
            return
        }
        #expect(refreshed.data.soldOut == updated.data.soldOut)
        #expect(!model.isRefreshing)
        await model.loadIfNeeded(apiClient: client, favorites: ComedianFavoriteStore(), cache: cache)
        #expect(transport.capturedRequests.count == 1)
    }

    @Test("club highlights revalidate upcoming shows after the freshness interval")
    func clubHighlightsRefreshAfterExpiry() async throws {
        var now = Date(timeIntervalSince1970: 1_000)
        let model = ClubHighlightsModel(clubId: 201, now: { now })
        let show = makeShow(id: 301, lineup: [])
        let first = Components.Schemas.ClubHighlightsResponse(data: .init(tonightShows: [], nextShow: show, frequentPerformers: []))
        let second = Components.Schemas.ClubHighlightsResponse(data: .init(tonightShows: [show], nextShow: nil, frequentPerformers: []))
        let firstBody = try APIMockEncoder.make().encode(first)
        let secondBody = try APIMockEncoder.make().encode(second)
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "getClubHighlights")
            return (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(firstBody))
        }
        let client = Client(serverURL: URL(string: "https://test.example.com")!, configuration: .laughTrack, transport: transport)
        await model.loadIfNeeded(apiClient: client)
        transport.setHandler { _, _, _, _ in
            (HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]), HTTPBody(secondBody))
        }
        await model.loadIfNeeded(apiClient: client)
        #expect(transport.capturedRequests.isEmpty)
        now = now.addingTimeInterval(60)
        await model.loadIfNeeded(apiClient: client)
        guard case .success(let refreshed) = model.phase else {
            Issue.record("Expected refreshed club highlights")
            return
        }
        #expect(refreshed.tonightShows.map(\.id) == [show.id])
        #expect(refreshed.nextShow == nil)
        #expect(transport.capturedRequests.count == 1)
    }

    @Test("failed explicit refresh remains retryable even inside the previous freshness window")
    func explicitFailureAllowsAutomaticRetry() async {
        let model = EntityDetailModel<Int>(now: { Date(timeIntervalSince1970: 1_000) })
        await model.loadIfNeeded(freshness: 60) { .success(1) }
        await model.refresh { .failure(.network("Offline")) }
        #expect(value(model) == 1)
        await model.loadIfNeeded(freshness: 60) { .success(2) }
        #expect(value(model) == 2)
        #expect(model.refreshFailure == nil)
    }

    #if canImport(UIKit)
    @Test("refresh and failed retry retain the mounted detail subtree and its filter state")
    func refreshKeepsMountedDetailState() async throws {
        let model = EntityDetailModel<Int>()
        await model.loadIfNeeded { .success(1) }
        let probe = DetailRefreshMountProbe()
        let host = HostedView(DetailRefreshMountView(model: model, probe: probe))
        _ = try host.snapshot() // Attach this test host before measuring its scroll view.
        await host.settle()
        #expect(probe.mounts == 1)
        probe.requestedFilter = "Weekend"
        await host.settle()
        probe.probe += 1
        await host.settle()
        #expect(probe.observedFilter == "Weekend")
        host.scrollDown(pages: 0.3)
        await host.settle()
        let metrics = try #require(host.scrollMetrics())
        let offset = metrics.offset
        #expect(offset > 0)
        let gate = DetailCancellationResponseGate()
        defer { gate.resolveAll() }
        let refresh = Task { await model.refresh { await gate.fetch() } }
        try await gate.waitForRequests(1)
        await host.settle()
        #expect(probe.mounts == 1)
        #expect(abs((host.scrollMetrics()?.offset ?? -1) - offset) < 1)
        try saveRefreshSnapshot(host, state: "pending")
        gate.resolve(0, .failure(.network("Offline")))
        await refresh.value
        await host.settle()
        #expect(probe.mounts == 1)
        #expect(abs((host.scrollMetrics()?.offset ?? -1) - offset) < 1)
        try saveRefreshSnapshot(host, state: "failure")
        // Clear the external request: only the mounted child's State retains it.
        probe.requestedFilter = nil
        await model.refresh { .success(2) }
        await host.settle()
        probe.probe += 1
        await host.settle()
        #expect(probe.mounts == 1)
        #expect(probe.observedFilter == "Weekend")
        #expect(abs((host.scrollMetrics()?.offset ?? -1) - offset) < 1)
        try saveRefreshSnapshot(host, state: "success")
    }

    private func saveRefreshSnapshot(_ host: HostedView, state: String) throws {
        let data = try #require(try host.snapshot().pngData())
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4021-refresh-\(state).png")
        try data.write(to: path)
        print("Detail refresh snapshot: \(path.path)")
    }
    #endif

    private func value(_ model: EntityDetailModel<Int>) -> Int? {
        guard case .success(let value) = model.phase else { return nil }
        return value
    }
}

#if canImport(UIKit)
@MainActor
private final class DetailRefreshMountProbe: ObservableObject {
    var mounts = 0
    var observedFilter = ""
    @Published var requestedFilter: String?
    @Published var probe = 0
}

private struct DetailRefreshMountView: View {
    @ObservedObject var model: EntityDetailModel<Int>
    @ObservedObject var probe: DetailRefreshMountProbe

    var body: some View {
        switch model.phase {
        case .success(let value):
            VStack {
                DetailRefreshStatus(isRefreshing: model.isRefreshing, failure: model.refreshFailure) {
                    await model.refresh { .success(value) }
                }
                DetailRefreshStatefulChild(value: value, probe: probe)
            }
        default:
            Text("Loading or unavailable")
        }
    }
}

private struct DetailRefreshStatefulChild: View {
    let value: Int
    @ObservedObject var probe: DetailRefreshMountProbe
    @State private var selectedFilter = "Tonight"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("\(value): \(selectedFilter)")
                ForEach(0..<40) { row in Text("Upcoming show \(row)").frame(height: 44) }
            }.frame(maxWidth: .infinity, alignment: .leading).padding()
        }
            .onAppear { probe.mounts += 1 }
            .onReceive(probe.$requestedFilter) { if let filter = $0 { selectedFilter = filter } }
            .onReceive(probe.$probe) { _ in probe.observedFilter = selectedFilter }
    }
}
#endif
