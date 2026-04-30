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

@Suite("Favorites view content")
@MainActor
struct LibraryFavoritesViewTests {
    @Test("signed-in favorites view renders saved comedians favorite shows and derived clubs")
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
        // The favorites load lives on AppShellView, not LibraryView, so the store
        // is already populated by the time LibraryView appears in production. Mirror
        // that by loading directly before mounting — pre-population also dodges the
        // HostedView/`.task(id:)` scheduling flakiness called out in ios/CLAUDE.md.
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        let host = HostedView(
            LibraryView(apiClient: apiClient)
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(NavigationCoordinator<AppRoute>())
                .environmentObject(favorites)
                .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.favoritesHeader)
        try host.requireText("Favorites")
        try host.requireView(withIdentifier: LaughTrackViewTestID.favoritesComediansSection)
        try host.requireView(withIdentifier: LaughTrackViewTestID.favoritesShowsSection)
        try host.requireView(withIdentifier: LaughTrackViewTestID.favoritesClubsSection)
        try host.requireLabel("Taylor Tomlinson")
        try host.requireLabel("5 tracked show appearances")
        try host.requireLabel("Taylor Tomlinson at The Stand")
        try host.requireLabel("The Stand")
    }

    @Test("favorites primitive filter shows only matching favorite content")
    func favoritesPrimitiveFilterShowsOnlyMatchingContent() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "favorites-filter"
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
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        let host = HostedView(
            LibraryView(apiClient: apiClient, selectedPrimitive: .clubs)
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(NavigationCoordinator<AppRoute>())
                .environmentObject(favorites)
                .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.favoritesClubsSection)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.favoritesComediansSection) == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.favoritesShowsSection) == nil)
    }

    @Test("signed-out favorites view shows sign-in CTA and skips the favorites fetch")
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

        try host.requireText("Sign in to see your favorites")
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
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

        switch response {
        case .success(let payload):
            if operationID == "getFavorites" {
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(payload))
                )
            }
            if operationID == "searchShows" {
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(Self.favoriteShowsResponse))
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

    private static var favoriteShowsResponse: Components.Schemas.ShowSearchResponse {
        .init(
            data: [
                .init(
                    id: 901,
                    clubName: "The Stand",
                    date: Date().addingTimeInterval(60 * 60 * 24),
                    tickets: [],
                    name: "Taylor Tomlinson at The Stand",
                    socialData: nil,
                    lineup: [
                        .init(
                            name: "Taylor Tomlinson",
                            imageUrl: "https://example.com/taylor.png",
                            uuid: "comedian-uuid-1",
                            id: 101,
                            userId: nil,
                            socialData: .init(id: 101),
                            isFavorite: true,
                            showCount: 5
                        ),
                    ],
                    description: "A favorite comedian is on this bill.",
                    address: "116 E 16th St, New York, NY",
                    room: "Main Room",
                    imageUrl: "https://example.com/show.png",
                    soldOut: false,
                    distanceMiles: nil
                ),
            ],
            total: 1,
            filters: [],
            zipCapTriggered: false
        )
    }
}
#endif
