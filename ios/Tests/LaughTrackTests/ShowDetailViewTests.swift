#if canImport(UIKit)
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
    @Test("show detail loads live show data and renders core sections")
    func showDetailLoadsAndDisplaysSections() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "show-detail-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    response: .success(
                        DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
                    )
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.showDetailScreen)
        try host.requireLabel("Mark Normand and Friends")
        try host.requireLabel("Tonight’s bill")
        try host.requireLabel("Related shows")
    }

    @Test("show detail surfaces API failures explicitly")
    func showDetailShowsErrorState() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "show-detail-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .status(.notFound)),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("This show could not be found. (HTTP 404)")
    }

    @Test("show detail renders explicit empty states for missing optional sections")
    func showDetailShowsEmptyStates() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "show-detail-empty")
        var response = DemoContent.showDetailResponse(id: 302) ?? DemoContent.primaryShowDetail
        response.data.lineup = nil
        response.relatedShows = []
        response.data.tickets = nil
        response.data.cta = .init(url: nil, label: "Buy tickets", isSoldOut: false)
        response.data.showPageUrl = ""

        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(response)),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("Lineup details are not available yet.")
        try host.requireLabel("No related shows are available yet.")
        try host.requireLabel("Unavailable")
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

        #expect(facts.map(\.label) == ["When", "Tickets", "Venue", "Distance"])
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

        #expect(facts.map(\.label) == ["When", "Tickets", "Venue"])
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

    private func makeView(apiClient: Client, authManager: AuthManager) -> some View {
        ShowDetailView(showID: 301, apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(ComedianFavoriteStore())
            .environmentObject(authManager)
    }

    private func makeClient(response: MockShowDetailTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockShowDetailTransport(response: response)
        )
    }
}

private struct MockShowDetailTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ShowDetailResponse)
        case status(HTTPResponse.Status)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        #expect(operationID == "getShow")
        #expect(request.method == .get)

        switch response {
        case .success(let payload):
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            // ErrorResponse schema requires `error` — empty `{}` makes the OpenAPI
            // decoder throw and the model falls into the network catch.
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(#"{"error":"mock"}"#)
            )
        }
    }
}
#endif
