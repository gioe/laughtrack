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

@Suite("Clubs search screen")
@MainActor
struct ClubsSearchScreenTests {
    @Test("clubs search screen loads live results and exposes navigation to club detail")
    func clubsSearchLoadsLiveResultsAndNavigatesToClubDetail() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "clubs-search-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse())),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.clubsSearchScreen)
        try host.requireLabel("Search live clubs")
        try host.requireLabel("Comedy Cellar")

        try host.tapControl(withIdentifier: LaughTrackViewTestID.clubsSearchResultButton(201))

        #expect(coordinator.path.last == .clubDetail(201))
    }

    @Test("clubs search screen surfaces an explicit loading state")
    func clubsSearchShowsLoadingState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "clubs-search-loading")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .delayedSuccess(makeResponse(), nanoseconds: 400_000_000)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Loading")
    }

    @Test("clubs search screen surfaces an explicit empty state")
    func clubsSearchShowsEmptyState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "clubs-search-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse(data: [], total: 0))),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Nothing here yet")
        try host.requireLabel("No clubs are available right now.")
    }

    @Test("clubs search screen surfaces an explicit error state")
    func clubsSearchShowsErrorState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "clubs-search-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .status(.internalServerError)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Couldn’t load this section")
        try host.requireLabel("LaughTrack could not load clubs right now.")
    }

    private func makeView(
        apiClient: Client,
        coordinator: NavigationCoordinator<AppRoute>,
        authManager: AuthManager
    ) -> some View {
        ClubsSearchScreen(apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
    }

    private func makeClient(response: MockClubsSearchTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockClubsSearchTransport(response: response)
        )
    }

    private func makeResponse(
        data: [Components.Schemas.ClubSearchItem] = mockClubs,
        total: Int? = nil
    ) -> Components.Schemas.ClubSearchResponse {
        .init(
            data: data,
            total: total ?? data.count,
            filters: []
        )
    }
}

private let mockClubs: [Components.Schemas.ClubSearchItem] = [
    .init(
        id: 201,
        address: "117 MacDougal St, New York, NY",
        name: "Comedy Cellar",
        zipCode: "10012",
        imageUrl: "https://example.com/club-201.jpg",
        showCount: 14,
        isFavorite: nil,
        city: "New York",
        state: "NY",
        phoneNumber: "(212) 254-3480",
        socialData: nil,
        activeComedianCount: 62,
        distanceMiles: nil
    )
]

private struct MockClubsSearchTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ClubSearchResponse)
        case delayedSuccess(Components.Schemas.ClubSearchResponse, nanoseconds: UInt64)
        case status(HTTPResponse.Status)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        #expect(operationID == "searchClubs")
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
        _ payload: Components.Schemas.ClubSearchResponse
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
