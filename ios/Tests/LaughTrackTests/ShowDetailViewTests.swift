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
        // Clear both ticket URL surfaces so the view renders the empty-tickets card.
        // ShowDetailView falls back from cta.url to showPageUrl; if either is set,
        // the rendered tree shows a "Buy tickets" / "Open show page" button instead.
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
        try host.requireLabel("Tickets are not linked yet for this show.")
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
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601

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
