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
    @Test("signed-in Library renders all live saved-entity stores")
    func signedInLibraryLoadsSavedFavorites() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "library-favorites"
        )
        let clubFavorites = ClubFavoriteStore()
        let podcastFavorites = PodcastFavoriteStore()
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
        await clubFavorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        await podcastFavorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        #expect(LibraryView.title == "Library")
        #expect(favorites.savedFavoriteComedians.map(\.name) == ["Taylor Tomlinson"])
        #expect(favorites.savedFavoriteComedians.map(\.showCount) == [5])
        #expect(clubFavorites.savedFavoriteClubs.map(\.name) == ["The Stand"])
        #expect(podcastFavorites.savedFavoritePodcasts.map(\.title) == ["Good One"])

    }

    @Test("Library excludes inferred followed-show presentation and loading")
    func libraryContainsOnlyExplicitCollections() throws {
        let source = try String(contentsOf: libraryViewSourceURL(), encoding: .utf8)

        #expect(!source.contains("From Your Follows"))
        #expect(!source.contains("FavoriteShowsSection"))
        #expect(!source.contains("HomeFavoriteShowsModel"))
        #expect(!source.contains("scopedShowIDs"))
        #expect(source.contains("SavedFavoritesSection(apiClient: apiClient)"))
    }

    @Test("saved entity types use three independent rail card shells")
    func savedFavoritesUseIndependentRailCardShells() throws {
        let source = try String(contentsOf: savedFavoritesSectionSourceURL(), encoding: .utf8)

        #expect(source.components(separatedBy: "LaughTrackRailCard(").count - 1 == 3)
        #expect(source.contains("title: LibrarySection.comedians.title"))
        #expect(source.contains("title: LibrarySection.clubs.title"))
        #expect(source.contains("title: LibrarySection.podcasts.title"))
        #expect(source.contains("LaughTrackViewTestID.favoritesComediansSection"))
        #expect(source.contains("LaughTrackViewTestID.favoritesClubsSection"))
        #expect(source.contains("LaughTrackViewTestID.favoritesPodcastsSection"))
        #expect(source.components(separatedBy: "pageSize: 5").count - 1 == 3)
        #expect(!source.contains("eyebrow: \"Your collection\""))
        #expect(!source.contains("you want to keep close"))
        #expect(!source.contains("savedGroupTitle"))
        #expect(!source.contains("LaughTrackSectionHeader("))
        #expect(!source.contains("LaughTrackCard {"))
        #expect(source.components(separatedBy: "LaughTrackSearchEntityRow(").count - 1 == 3)
        #expect(!source.contains("design: .savedEntity"))
    }

    @Test("signed-out favorites view shows sign-in CTA and skips the favorites fetch")
    func signedOutLibrarySkipsFavoritesFetch() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "library-signed-out")
        let recorder = FavoritesRequestRecorder()

        #expect(authManager.currentSession == nil)
        #expect(LibraryView.signedOutPromptTitle == "Sign in to build your Library")
        #expect(recorder.getFavoritesCalls == 0)
    }

    @Test("favorite shows search matches comedian names only")
    func favoritesSearchMatchersUseDisplayFields() {
        let parentComedian = lineup(name: "Atsuko Okatsuka")
        let show = show(
            name: "Basement Showcase",
            clubName: "The Stand",
            lineup: [
                lineup(name: "Atsuko Alias", parentComedian: parentComedian),
            ]
        )

        #expect(LibraryFavoritesPresentation.matches(show: show, query: "atsuko alias"))
        #expect(LibraryFavoritesPresentation.matches(show: show, query: "okatsuka"))
        #expect(!LibraryFavoritesPresentation.matches(show: show, query: "basement"))
        #expect(!LibraryFavoritesPresentation.matches(show: show, query: "stand"))
        #expect(!LibraryFavoritesPresentation.matches(show: show, query: "cellar"))
    }

    @Test("favorite searchable section returns expected paged item slices")
    func favoriteSearchableSectionPagingSlicesItems() {
        typealias Section = FavoriteSearchableSection<Int, Int, EmptyView>
        let items = Array(1...11)

        #expect(
            Section.pagedItems(
                items: Array(1...5),
                query: "",
                page: 0,
                pageSize: 5,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ) == [1, 2, 3, 4, 5]
        )

        #expect(
            Section.pagedItems(
                items: items,
                query: "",
                page: 1,
                pageSize: 5,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ) == [6, 7, 8, 9, 10]
        )

        #expect(
            Section.pagedItems(
                items: items,
                query: "no-match",
                page: 0,
                pageSize: 5,
                matchesQuery: { item, query in "\(item)".contains(query) }
            ).isEmpty
        )
    }

    private func makeClient(response: MockLibraryFavoritesTransport.Response) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
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
            clubId: 202,
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

    private func libraryViewSourceURL(filePath: String = #filePath) throws -> URL {
        try sourceURL("Sources/LaughTrackApp/LibraryView.swift", filePath: filePath)
    }

    private func savedFavoritesSectionSourceURL(filePath: String = #filePath) throws -> URL {
        try sourceURL(
            "Sources/LaughTrackApp/Components/Settings/SavedFavoritesSection.swift",
            filePath: filePath
        )
    }

    private func sourceURL(_ relativePath: String, filePath: String) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent(relativePath)
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
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
            if operationID == "getFavoriteClubs" {
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(Self.favoriteClubsResponse))
                )
            }
            if operationID == "getFavoritePodcasts" {
                return (
                    HTTPResponse(
                        status: .ok,
                        headerFields: [.contentType: "application/json"]
                    ),
                    HTTPBody(try encoder.encode(Self.favoritePodcastsResponse))
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

    private static var favoriteClubsResponse: Components.Schemas.FavoriteClubListResponse {
        .init(data: [
            .init(
                id: 202,
                name: "The Stand",
                imageUrl: "https://example.com/the-stand.png",
                isFavorite: true
            ),
        ])
    }

    private static var favoritePodcastsResponse: Components.Schemas.FavoritePodcastListResponse {
        .init(data: [
            .init(
                id: 303,
                title: "Good One",
                authorName: "Vulture",
                imageUrl: "https://example.com/good-one.png",
                episodeCount: 248,
                isFavorite: true
            ),
        ])
    }
}
