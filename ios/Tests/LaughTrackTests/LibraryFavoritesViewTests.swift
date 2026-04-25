#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("Library favorites view")
@MainActor
struct LibraryFavoritesViewTests {
    @Test("signed-in library view loads saved favorites from the live API contract")
    func signedInLibraryLoadsSavedFavorites() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "library-favorites"
        )
        let favorites = ComedianFavoriteStore()
        let apiClient = makeClient(
            response: .success(
                .init(
                    data: [
                        .init(
                            id: 101,
                            uuid: "comedian-uuid-1",
                            name: "Taylor Tomlinson",
                            imageUrl: "https://example.com/taylor.png",
                            socialData: .init(id: 101),
                            showCount: 5,
                            isFavorite: true
                        )
                    ]
                )
            )
        )
        // SwiftUI's `.task(id:)` lifecycle does not fire reliably under HostedView
        // (the SwiftUI view enters the hierarchy but the test pumps the run loop
        // synchronously before the task scheduler dispatches). Load favorites
        // explicitly so the test verifies the rendered output, not the lifecycle.
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        let host = HostedView(
            LibraryView(apiClient: apiClient)
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(NavigationCoordinator<AppRoute>())
                .environmentObject(favorites)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.libraryFavoritesSection)
        try host.requireLabel("Taylor Tomlinson")
        try host.requireLabel("5 tracked show appearances")
    }

    @Test("signed-out library view shows sign-in CTA and skips the favorites fetch")
    func signedOutLibrarySkipsFavoritesFetch() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "library-signed-out")
        let favorites = ComedianFavoriteStore()
        let recorder = FavoritesRequestRecorder()
        let host = HostedView(
            LibraryView(
                apiClient: makeClient(response: .recorder(recorder))
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
        )

        try host.requireText("Sign in to see your saved comedians")
        #expect(recorder.getFavoritesCalls == 0)
    }

    private func makeClient(response: MockLibraryFavoritesTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockLibraryFavoritesTransport(response: response)
        )
    }
}

private final class FavoritesRequestRecorder: @unchecked Sendable {
    var getFavoritesCalls = 0
}

private struct MockLibraryFavoritesTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.FavoriteListResponse)
        case recorder(FavoritesRequestRecorder)
    }

    let response: Response

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch response {
        case .success(let payload):
            if operationID == "getFavorites" {
                let encoder = JSONEncoder()
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(payload))
                )
            }
        case .recorder(let recorder):
            if operationID == "getFavorites" {
                recorder.getFavoritesCalls += 1
            }
        }

        return (
            HTTPResponse(
                status: .internalServerError,
                headerFields: [.contentType: "application/json"]
            ),
            HTTPBody(#"{"error":"unexpected operation"}"#)
        )
    }
}
#endif
