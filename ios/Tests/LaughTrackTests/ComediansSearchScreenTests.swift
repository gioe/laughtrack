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

@Suite("Comedians search screen")
@MainActor
struct ComediansSearchScreenTests {
    @Test("comedians search screen loads live results and exposes navigation to comedian detail")
    func comediansSearchLoadsLiveResultsAndNavigatesToComedianDetail() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedians-search-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse())),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.comediansSearchScreen)
        try host.requireLabel("Search live comedians")
        try host.requireLabel("Mark Normand")
        try host.requireLabel("Comedians in rotation")

        try host.tapControl(withIdentifier: LaughTrackViewTestID.comediansSearchResultButton(101))

        #expect(coordinator.path.last == .comedianDetail(101))
    }

    @Test("comedians search screen surfaces an explicit loading state")
    func comediansSearchShowsLoadingState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedians-search-loading")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .delayedSuccess(makeResponse(), nanoseconds: 400_000_000)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Loading comedians")
    }

    @Test("comedians search screen surfaces an explicit empty state")
    func comediansSearchShowsEmptyState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedians-search-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .success(makeResponse(data: [], total: 0))),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("No comedians yet")
        try host.requireLabel("No comedians are available right now.")
    }

    @Test("comedians search screen surfaces an explicit error state")
    func comediansSearchShowsErrorState() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedians-search-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(response: .status(.internalServerError)),
                coordinator: coordinator,
                authManager: authManager
            )
        )

        try host.requireLabel("Couldn’t load comedians")
        try host.requireLabel("LaughTrack could not load comedians right now.")
    }

    private func makeView(
        apiClient: Client,
        coordinator: NavigationCoordinator<AppRoute>,
        authManager: AuthManager
    ) -> some View {
        ComediansSearchScreen(apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
    }

    private func makeClient(response: MockComediansSearchTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockComediansSearchTransport(response: response)
        )
    }

    private func makeResponse(
        data: [Components.Schemas.ComedianSearchItem] = mockComedians,
        total: Int? = nil
    ) -> Components.Schemas.ComedianSearchResponse {
        .init(
            data: data,
            total: total ?? data.count,
            filters: []
        )
    }
}

private let mockComedians: [Components.Schemas.ComedianSearchItem] = [
    .init(
        id: 101,
        uuid: "comedian-101",
        name: "Mark Normand",
        imageUrl: "https://example.com/mark.jpg",
        socialData: .init(
            instagramAccount: "marknormand",
            youtubeAccount: "marknormand",
            tiktokAccount: nil,
            website: "https://example.com/mark",
            linktree: nil,
            twitterAccount: nil,
            spotifyAccount: nil,
            appleMusicAccount: nil,
            soundcloudAccount: nil,
            bandcampAccount: nil
        ),
        showCount: 12,
        isFavorite: false
    )
]

private struct MockComediansSearchTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ComedianSearchResponse)
        case delayedSuccess(Components.Schemas.ComedianSearchResponse, nanoseconds: UInt64)
        case status(HTTPResponse.Status)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        #expect(operationID == "searchComedians")
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
        _ payload: Components.Schemas.ComedianSearchResponse
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
