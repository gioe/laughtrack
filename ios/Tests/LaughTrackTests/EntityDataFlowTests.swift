import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
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

    @Test("home favorite shows model matches shows by favorited lineup identity")
    func homeFavoriteShowsMatchFavoritedLineupIdentity() {
        let favorite = Components.Schemas.ComedianSearchItem(
            id: 501,
            uuid: "comedian-taylor",
            name: "Taylor Tomlinson",
            imageUrl: "https://example.com/taylor.png",
            socialData: .init(id: 501),
            showCount: 4,
            isFavorite: true
        )
        let matchingShow = makeShow(
            id: 901,
            lineup: [
                .init(
                    name: "Taylor Tomlinson",
                    imageUrl: "https://example.com/taylor.png",
                    uuid: "comedian-taylor",
                    id: 501,
                    userId: nil,
                    socialData: .init(id: 501),
                    isFavorite: true,
                    showCount: 4
                ),
            ]
        )
        let unrelatedShow = makeShow(
            id: 902,
            lineup: [
                .init(
                    name: "Different Comic",
                    imageUrl: "https://example.com/different.png",
                    uuid: "comedian-different",
                    id: 777,
                    userId: nil,
                    socialData: .init(id: 777),
                    isFavorite: false,
                    showCount: 1
                ),
            ]
        )

        #expect(HomeFavoriteShowsModel.show(matchingShow, matches: favorite))
        #expect(!HomeFavoriteShowsModel.show(unrelatedShow, matches: favorite))
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

    @Test("home shows tonight model renders raw API show dates from a 200 home feed")
    func homeShowsTonightModelDecodesRawHomeFeedDates() async {
        let model = HomeShowsTonightModel()
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: RawShowRailTransport()
        )

        await model.refresh(apiClient: client, zipCode: nil)

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected home shows tonight to decode the 200 home feed")
            return
        }

        #expect(shows.map(\.id) == [101])
        #expect(model.cityTitle == "New York, NY")
    }

    @Test("shows discovery model renders raw API show dates from a 200 search response")
    func showsDiscoveryModelDecodesRawSearchDates() async {
        let model = ShowsDiscoveryModel(
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
            return jsonResponse(
                """
                {
                  "data": {
                    "hero": {
                      "zipCode": "10012",
                      "city": "New York",
                      "state": "NY",
                      "shows": []
                    },
                    "trendingComedians": [],
                    "comediansNearYou": [],
                    "showsTonight": [
                      {
                        "id": 101,
                        "date": "2026-04-29T00:00:00.000Z",
                        "name": "Tonight Show",
                        "clubName": "New York Comedy Club",
                        "imageUrl": "https://example.com/show.png",
                        "lineup": [],
                        "tickets": [
                          {
                            "price": 9.0,
                            "purchaseUrl": "https://example.com/tickets",
                            "type": "General Admission",
                            "soldOut": false
                          }
                        ]
                      }
                    ],
                    "moreNearYou": [],
                    "trendingThisWeek": [],
                    "popularClubs": []
                  }
                }
                """
            )
        case "searchShows":
            return jsonResponse(
                """
                {
                  "data": [
                    {
                      "id": 201,
                      "date": "2026-05-27T02:30:00.000Z",
                      "name": "Search Show",
                      "clubName": "Flappers Comedy Club And Restaurant Burbank",
                      "imageUrl": "/placeholders/club-placeholder.svg",
                      "soldOut": false,
                      "lineup": [],
                      "tickets": []
                    }
                  ],
                  "total": 1,
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
