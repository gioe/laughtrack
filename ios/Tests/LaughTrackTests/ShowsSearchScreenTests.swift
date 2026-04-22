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

@Suite("Shows search screen")
@MainActor
struct ShowsSearchScreenTests {
    @Test("shows search screen loads live results and exposes navigation to show detail")
    func showsSearchLoadsLiveResultsAndNavigatesToShowDetail() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shows-search-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse())),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.showsSearchScreen)
        try host.requireLabel("Search live shows")
        try host.requireLabel("Mark Normand and Friends")

        try host.tapControl(withIdentifier: LaughTrackViewTestID.showsSearchResultButton(301))

        #expect(coordinator.path.last == .showDetail(301))
    }

    @Test("shows search screen surfaces an explicit loading state")
    func showsSearchShowsLoadingState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shows-search-loading")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .delayedSuccess(makeResponse(), nanoseconds: 400_000_000)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Loading")
    }

    @Test("shows search screen surfaces an explicit empty state")
    func showsSearchShowsEmptyState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shows-search-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse(data: [], total: 0))),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Nothing here yet")
        try host.requireLabel("No shows are available right now.")
    }

    @Test("shows search screen surfaces an explicit error state")
    func showsSearchShowsErrorState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shows-search-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .status(.internalServerError)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Couldn’t load this section")
        try host.requireLabel("LaughTrack could not load shows right now.")
    }

    private func makeView(
        apiClient: Client,
        coordinator: NavigationCoordinator<AppRoute>,
        authManager: AuthManager
    ) -> some View {
        ShowsSearchScreen(
            apiClient: apiClient,
            nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "shows-search-screen")
        )
        .environment(\.appTheme, LaughTrackTheme())
        .navigationCoordinator(coordinator)
        .environmentObject(authManager)
    }

    private func makeClient(response: MockShowsSearchTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockShowsSearchTransport(response: response)
        )
    }

    private func makeResponse(
        data: [Components.Schemas.Show] = mockShows,
        total: Int? = nil
    ) -> Components.Schemas.ShowSearchResponse {
        .init(
            data: data,
            total: total ?? data.count,
            filters: [],
            zipCapTriggered: false
        )
    }
}

private let mockShows: [Components.Schemas.Show] = [
    .init(
        id: 301,
        clubName: "Comedy Cellar",
        date: Date(timeIntervalSince1970: 1_710_000_000),
        tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/tickets/301", soldOut: false, _type: "General admission")],
        name: "Mark Normand and Friends",
        socialData: nil,
        lineup: nil,
        description: "A live backend show fixture for the dedicated search screen tests.",
        address: "117 MacDougal St, New York, NY",
        room: "Main Room",
        imageUrl: "https://example.com/show-301.jpg",
        soldOut: false,
        distanceMiles: 2.1
    )
]

private struct MockShowsSearchTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ShowSearchResponse)
        case delayedSuccess(Components.Schemas.ShowSearchResponse, nanoseconds: UInt64)
        case status(HTTPResponse.Status)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        #expect(operationID == "searchShows")
        #expect(request.method == .get)

        switch response {
        case .success(let payload):
            return try makeSuccessResponse(payload)
        case .delayedSuccess(let payload, let nanoseconds):
            try await Task.sleep(nanoseconds: nanoseconds)
            return try makeSuccessResponse(payload)
        case .status(let status):
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody("{}")
            )
        }
    }

    private func makeSuccessResponse(
        _ payload: Components.Schemas.ShowSearchResponse
    ) throws -> (HTTPResponse, HTTPBody?) {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

        return (
            HTTPResponse(
                status: .ok,
                headerFields: [.contentType: "application/json"]
            ),
            HTTPBody(try encoder.encode(payload))
        )
    }
}
#endif
