import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Show detail view")
@MainActor
struct ShowDetailViewTests {
    @Test("show detail model loads live show data for core sections")
    func showDetailModelLoadsCoreSectionState() async throws {
        let model = ShowDetailModel(showID: 301)
        let favorites = ComedianFavoriteStore()

        await model.loadIfNeeded(
            apiClient: makeClient(
                response: .success(
                    DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
                )
            ),
            favorites: favorites
        )

        guard case .success(let response) = model.phase else {
            Issue.record("Expected show detail success phase, got \(model.phase)")
            return
        }

        #expect(response.data.name == "Mark Normand and Friends")
        #expect(response.data.lineup?.map(\.name) == ["Mark Normand", "Atsuko Okatsuka", "Sam Morril"])
        #expect(response.relatedShows.map(\.id) == [302])
        #expect(ShowDetailPresentation.summaryFacts(for: response.data).map(\.label) == ["When", "Venue", "Distance", "Tickets"])
        #expect(favorites.value(for: "demo-comedian-101") == false)
        #expect(favorites.value(for: "demo-comedian-102") == true)
    }

    @Test("show detail model surfaces API failures explicitly")
    func showDetailModelShowsErrorState() async throws {
        let model = ShowDetailModel(showID: 301)

        await model.loadIfNeeded(
            apiClient: makeClient(response: .status(.notFound)),
            favorites: ComedianFavoriteStore()
        )

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected show detail failure phase, got \(model.phase)")
            return
        }

        #expect(failure.message == "This show could not be found. (HTTP 404)")
    }

    @Test("show detail model keeps empty optional section state explicit")
    func showDetailModelKeepsEmptySectionState() async throws {
        var response = DemoContent.showDetailResponse(id: 302) ?? DemoContent.primaryShowDetail
        response.data.lineup = nil
        response.relatedShows = []
        response.data.tickets = nil
        response.data.cta = .init(url: nil, label: "Buy tickets", isSoldOut: false)
        response.data.showPageUrl = ""
        let model = ShowDetailModel(showID: 301)

        await model.loadIfNeeded(
            apiClient: makeClient(response: .success(response)),
            favorites: ComedianFavoriteStore()
        )

        guard case .success(let loaded) = model.phase else {
            Issue.record("Expected show detail success phase, got \(model.phase)")
            return
        }

        #expect(loaded.data.lineup == nil)
        #expect(loaded.relatedShows.isEmpty)
        #expect(ShowDetailPresentation.summaryFacts(for: loaded.data).first { $0.label == "Tickets" }?.value == "Unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: loaded.data) == nil)
    }

    @Test("show detail favorite toggle dispatches through the favorite API boundary")
    func showDetailFavoriteToggleDispatchesFavoriteAPI() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "show-detail-favorite-toggle"
        )
        let recorder = FavoriteOperationRecorder()
        let client = makeClient(
            response: .success(DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail),
            favoriteRecorder: recorder
        )
        let favorites = ComedianFavoriteStore()
        let model = ShowDetailModel(showID: 301)
        await model.loadIfNeeded(apiClient: client, favorites: favorites)

        let initialOperations = await recorder.operations
        #expect(initialOperations == ["getShow"])
        #expect(favorites.value(for: "demo-comedian-101") == false)

        let result = await favorites.toggle(
            uuid: "demo-comedian-101",
            currentValue: favorites.value(for: "demo-comedian-101"),
            apiClient: client,
            authManager: authManager
        )

        guard case .updated(let nextValue) = result else {
            Issue.record("Expected favorite toggle to update, got \(result)")
            return
        }

        let finalOperations = await recorder.operations
        #expect(nextValue == true)
        #expect(favorites.value(for: "demo-comedian-101") == true)
        #expect(finalOperations == ["getShow", "addFavorite"])
    }

    @Test("show detail navigation actions push the expected route payloads")
    func showDetailNavigationActionsPushRoutePayloads() throws {
        let response = DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
        let show = response.data
        let firstComedian = try #require(show.lineup?.first)
        let firstRelated = try #require(response.relatedShows.first)
        let coordinator = NavigationCoordinator<AppRoute>()
        let targets: [EntityNavigationTarget] = [
            .club(show.club.id),
            .comedian(firstComedian.id),
            .show(firstRelated.id),
        ]
        let expectedRoutes: [AppRoute] = [
            .clubDetail(201),
            .comedianDetail(101),
            .showDetail(302),
        ]

        #expect(targets.map(\.route) == expectedRoutes)

        targets.forEach { coordinator.open($0) }

        #expect(coordinator.path.count == expectedRoutes.count)
    }

    @Test("show detail hero does not duplicate summary facts")
    func showHeroBadgesAreEmpty() {
        let show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data

        #expect(ShowDetailPresentation.heroBadges(for: show).isEmpty)
    }

    @Test("show detail summary facts include event operations")
    func showSummaryFactsIncludeOperationalDetails() {
        let show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Distance", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "$30.00")
        #expect(facts.first { $0.label == "Venue" }?.value == "Comedy Cellar")
        #expect(facts.first { $0.label == "Distance" }?.value == "2.1 miles away")
    }

    @Test("show detail summary facts omit missing optional values and address")
    func showSummaryFactsOmitMissingValuesAndAddress() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = nil
        show.room = nil
        show.distanceMiles = nil
        show.address = "318 W. 53rd St, New York, NY"
        show.club.address = "318 W. 53rd St, New York, NY"

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "Unavailable")
    }

    @Test("show detail ticket cell targets ticket purchase URL")
    func showTicketCellTargetsTicketPurchaseURL() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = [
            .init(price: 30, purchaseUrl: "https://laughtrack.app/ticket-option", soldOut: false, _type: "General admission")
        ]
        show.cta = .init(url: "https://laughtrack.app/show-cta", label: "Buy tickets", isSoldOut: false)

        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://laughtrack.app/ticket-option")
    }

    @Test("show detail calendar event uses show venue and ticket URL")
    func showCalendarEventUsesShowVenueAndTicketURL() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = [
            .init(price: 30, purchaseUrl: "https://laughtrack.app/ticket-option", soldOut: false, _type: "General admission")
        ]

        let event = ShowCalendarEventPresentation.event(for: show)

        #expect(event.title == show.name)
        #expect(event.startDate == show.date)
        #expect(event.endDate == show.date.addingTimeInterval(2 * 60 * 60))
        #expect(event.location?.contains(show.club.name) == true)
        #expect(event.url?.absoluteString == "https://laughtrack.app/ticket-option")
    }

    private func makeClient(
        response: MockShowDetailTransport.Response,
        favoriteRecorder: FavoriteOperationRecorder? = nil
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockShowDetailTransport(response: response, favoriteRecorder: favoriteRecorder)
        )
    }
}

private actor FavoriteOperationRecorder {
    private(set) var operations: [String] = []

    func record(_ operation: String) {
        operations.append(operation)
    }
}

private struct MockShowDetailTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ShowDetailResponse)
        case status(HTTPResponse.Status)
    }

    let response: Response
    let favoriteRecorder: FavoriteOperationRecorder?

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        await favoriteRecorder?.record(operationID)

        if operationID == "addFavorite" || operationID == "removeFavorite" {
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(
                    try encoder.encode(
                        Components.Schemas.FavoriteResponse(
                            data: .init(isFavorited: operationID == "addFavorite")
                        )
                    )
                )
            )
        }

        #expect(operationID == "getShow")
        #expect(request.method == .get)

        switch response {
        case .success(let payload):
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            // ErrorResponse schema requires `error` — empty `{}` makes the OpenAPI
            // decoder throw and the model falls into the network catch.
            return (
                HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"mock"}"#)
            )
        }
    }
}
