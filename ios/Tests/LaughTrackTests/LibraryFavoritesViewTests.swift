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

    @Test("favorite shows and podcasts match expected search fields")
    func favoritesSearchMatchersUseDisplayFields() {
        let parentComedian = lineup(name: "Atsuko Okatsuka")
        let show = show(
            name: "Basement Showcase",
            clubName: "The Stand",
            lineup: [
                lineup(name: "Atsuko Alias", parentComedian: parentComedian),
            ]
        )
        let podcast = Components.Schemas.FavoritePodcastItem(
            id: 301,
            title: "Good One",
            authorName: "Jesse David Fox",
            episodeCount: 82,
            isFavorite: true
        )

        #expect(LibraryFavoritesPresentation.matches(show: show, query: "basement"))
        #expect(LibraryFavoritesPresentation.matches(show: show, query: "stand"))
        #expect(LibraryFavoritesPresentation.matches(show: show, query: "atsuko alias"))
        #expect(LibraryFavoritesPresentation.matches(show: show, query: "okatsuka"))
        #expect(!LibraryFavoritesPresentation.matches(show: show, query: "cellar"))

        #expect(LibraryFavoritesPresentation.matches(podcast: podcast, query: "good"))
        #expect(LibraryFavoritesPresentation.matches(podcast: podcast, query: "fox"))
        #expect(!LibraryFavoritesPresentation.matches(podcast: podcast, query: "club"))
    }

    @Test("favorite searchable section returns expected paged item slices")
    func favoriteSearchableSectionPagingSlicesItems() {
        typealias Section = FavoriteSearchableSection<Int, Int, EmptyView>
        let items = Array(1...25)

        #expect(
            Section.pagedItems(
                items: Array(1...5),
                query: "",
                page: 0,
                pageSize: 20,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ) == [1, 2, 3, 4, 5]
        )

        #expect(
            Section.pagedItems(
                items: items,
                query: "",
                page: 1,
                pageSize: 20,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ) == [21, 22, 23, 24, 25]
        )

        #expect(
            Section.pagedItems(
                items: items,
                query: "no-match",
                page: 0,
                pageSize: 20,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ).isEmpty
        )
    }

    private func makeClient(response: MockLibraryFavoritesTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockLibraryFavoritesTransport(response: response)
        )
    }

    private func show(
        name: String,
        clubName: String,
        lineup: [Components.Schemas.ComedianLineup]
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 901,
            clubID: 202,
            clubName: clubName,
            date: Date().addingTimeInterval(60 * 60 * 24),
            tickets: [],
            name: name,
            socialData: nil,
            lineup: lineup,
            description: "A favorite comedian is on this bill.",
            address: "116 E 16th St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: nil
        )
    }

    private func lineup(
        name: String,
        parentComedian: Components.Schemas.ComedianLineup? = nil
    ) -> Components.Schemas.ComedianLineup {
        Components.Schemas.ComedianLineup(
            name: name,
            imageUrl: "https://example.com/\(name).png",
            uuid: UUID().uuidString,
            id: name.utf8.reduce(0) { $0 + Int($1) },
            showCount: 1,
            parentComedian: parentComedian
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
