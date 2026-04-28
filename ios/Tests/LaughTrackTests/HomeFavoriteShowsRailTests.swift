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

@Suite("Home favorite shows rail")
@MainActor
struct HomeFavoriteShowsRailTests {
    @Test("signed-in users with saved favorites see upcoming shows before trending")
    func signedInFavoritesShowRail() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "home-favorite-shows"
        )
        let favorites = ComedianFavoriteStore()
        let apiClient = makeClient(
            favoriteResponse: .init(data: [favoriteComedian]),
            showResponses: [
                "Taylor Tomlinson": .init(data: [favoriteShow], total: 1, filters: [], zipCapTriggered: false),
            ]
        )
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)

        let host = HostedView(
            homeView(apiClient: apiClient, authManager: authManager, favorites: favorites)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeFavoriteShowsRail)
        try host.requireText("Your favorites are touring")
        try host.requireLabel("Taylor Tomlinson at The Stand")
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeFavoriteShowButton(901))
    }

    @Test("signed-out users do not see the favorite shows rail")
    func signedOutHidesFavoriteShowsRail() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-favorite-signed-out")
        let favorites = ComedianFavoriteStore()
        let apiClient = makeClient(
            favoriteResponse: .init(data: [favoriteComedian]),
            showResponses: [
                "Taylor Tomlinson": .init(data: [favoriteShow], total: 1, filters: [], zipCapTriggered: false),
            ]
        )

        let host = HostedView(
            homeView(apiClient: apiClient, authManager: authManager, favorites: favorites)
        )
        await host.settle()

        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeFavoriteShowsRail) == nil)
    }

    @Test("signed-in users with zero favorites do not see the favorite shows rail")
    func emptyFavoritesHideFavoriteShowsRail() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "home-favorite-empty"
        )
        let favorites = ComedianFavoriteStore()
        let apiClient = makeClient(
            favoriteResponse: .init(data: []),
            showResponses: [:]
        )
        await favorites.loadSavedFavorites(apiClient: apiClient, authManager: authManager)

        let host = HostedView(
            homeView(apiClient: apiClient, authManager: authManager, favorites: favorites)
        )
        await host.settle()

        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeFavoriteShowsRail) == nil)
    }

    private func homeView(
        apiClient: Client,
        authManager: AuthManager,
        favorites: ComedianFavoriteStore
    ) -> some View {
        HomeView(
            apiClient: apiClient,
            signedOutMessage: nil,
            searchNavigationBridge: SearchNavigationBridge()
        )
        .environment(\.appTheme, LaughTrackTheme())
        .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-favorites-\(UUID().uuidString)"))
        .navigationCoordinator(NavigationCoordinator<AppRoute>())
        .environmentObject(authManager)
        .environmentObject(favorites)
    }

    private func makeClient(
        favoriteResponse: Components.Schemas.FavoriteListResponse,
        showResponses: [String: Components.Schemas.ShowSearchResponse]
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockHomeFavoriteShowsTransport(
                favoriteResponse: favoriteResponse,
                showResponses: showResponses
            )
        )
    }

    private var favoriteComedian: Components.Schemas.ComedianSearchItem {
        .init(
            id: 501,
            uuid: "comedian-taylor",
            name: "Taylor Tomlinson",
            imageUrl: "https://example.com/taylor.png",
            socialData: .init(id: 501),
            showCount: 4,
            isFavorite: true
        )
    }

    private var favoriteShow: Components.Schemas.Show {
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
                    uuid: "comedian-taylor",
                    id: 501,
                    userId: nil,
                    socialData: .init(id: 501),
                    isFavorite: true,
                    showCount: 4
                ),
            ],
            description: "A favorite comedian is on this bill.",
            address: "116 E 16th St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: nil
        )
    }
}

private struct MockHomeFavoriteShowsTransport: ClientTransport {
    let favoriteResponse: Components.Schemas.FavoriteListResponse
    let showResponses: [String: Components.Schemas.ShowSearchResponse]

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = JSONEncoder()

        switch operationID {
        case "getFavorites":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(favoriteResponse))
            )
        case "searchShows":
            let name = request.url?.queryItems["comedian"] ?? ""
            let response = showResponses[name] ??
                showResponses.values.first ??
                .init(data: [], total: 0, filters: [], zipCapTriggered: false)
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(response))
            )
        default:
            return (
                HTTPResponse(status: .internalServerError, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"unexpected operation"}"#)
            )
        }
    }
}

private extension URL {
    var queryItems: [String: String] {
        URLComponents(url: self, resolvingAgainstBaseURL: false)?
            .queryItems?
            .reduce(into: [:]) { result, item in
                result[item.name] = item.value
            } ?? [:]
    }
}
#endif
