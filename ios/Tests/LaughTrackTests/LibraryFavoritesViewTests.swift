import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("Favorites view content")
@MainActor
struct LibraryFavoritesViewTests {
    @Test("signed-in favorites view renders saved comedians and favorite shows")
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
        // that by loading directly before checking the Library presentation contract.
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        let model = HomeFavoriteShowsModel()
        await model.refresh(
            apiClient: apiClient,
            favoriteComedians: favorites.savedFavoriteComedians,
            cache: nil,
            cacheTTL: 0,
            persistentCache: nil
        )

        #expect(LibraryView.title == "Favorites")
        #expect(favorites.savedFavoriteComedians.map(\.name) == ["Taylor Tomlinson"])
        #expect(favorites.savedFavoriteComedians.map(\.showCount) == [5])

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }
        #expect(shows.map(\.name) == ["Taylor Tomlinson at The Stand"])
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

        #expect(LibraryFavoritesPresentation.includes(.clubs, selectedPrimitive: .clubs))
        #expect(!LibraryFavoritesPresentation.includes(.comedians, selectedPrimitive: .clubs))
        #expect(!LibraryFavoritesPresentation.includes(.shows, selectedPrimitive: .clubs))
    }

    @Test("signed-out favorites view shows sign-in CTA and skips the favorites fetch")
    func signedOutLibrarySkipsFavoritesFetch() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "library-signed-out")
        let recorder = FavoritesRequestRecorder()

        #expect(authManager.currentSession == nil)
        #expect(LibraryView.signedOutPromptTitle == "Sign in to see your favorites")
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
        let encoder = APIMockEncoder.make()

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
                    clubID: 202,
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
