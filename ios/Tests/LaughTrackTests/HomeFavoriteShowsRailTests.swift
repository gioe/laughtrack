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
    // TASK-1921 pilot for the model-layer test pattern under the iOS 26
    // accessibility-tree wiring regression. The original test asserted via
    // host.requireView / requireText / requireLabel after mounting HomeView
    // through HostedView; under iOS 26.1+ the HostingView's accessibility
    // tree is empty, so those assertions fail unconditionally regardless of
    // product correctness. See ios/CLAUDE.md "iOS 26 Accessibility-Tree
    // Wiring Regression" for the bisect data and migration pattern.
    @Test("favorite shows model loads upcoming shows for saved favorites")
    func favoriteShowsModelLoadsUpcomingShowsForSavedFavorites() async throws {
        let apiClient = makeClient(
            favoriteResponse: .init(data: [favoriteComedian]),
            showResponses: [
                "Taylor Tomlinson": .init(data: [favoriteShow], total: 1, filters: [], zipCapTriggered: false),
            ]
        )
        let model = HomeFavoriteShowsModel()

        await model.refresh(
            apiClient: apiClient,
            favoriteComedians: [favoriteComedian],
            cache: nil,
            persistentCache: nil
        )

        guard case let .success(shows) = model.phase else {
            Issue.record("Expected .success phase, got \(model.phase)")
            return
        }
        #expect(shows.map(\.name) == ["Taylor Tomlinson at The Stand"])
        #expect(shows.map(\.id) == [favoriteShow.id])
    }

    @Test("signed-out users do not see the favorite shows rail")
    func signedOutHidesFavoriteShowsRail() async throws {
        let apiClient = makeClient(
            favoriteResponse: .init(data: [favoriteComedian]),
            showResponses: [
                "Taylor Tomlinson": .init(data: [favoriteShow], total: 1, filters: [], zipCapTriggered: false),
            ]
        )
        let model = HomeFavoriteShowsModel()

        await model.refresh(
            apiClient: apiClient,
            favoriteComedians: [],
            cache: nil,
            persistentCache: nil
        )

        guard case .idle = model.phase else {
            Issue.record("Expected .idle phase for signed-out empty favorite input, got \(model.phase)")
            return
        }
    }

    @Test("signed-in users with zero favorites do not see the favorite shows rail")
    func emptyFavoritesHideFavoriteShowsRail() async throws {
        let apiClient = makeClient(
            favoriteResponse: .init(data: []),
            showResponses: [:]
        )
        let model = HomeFavoriteShowsModel()

        await model.refresh(
            apiClient: apiClient,
            favoriteComedians: [],
            cache: nil,
            persistentCache: nil
        )

        guard case .idle = model.phase else {
            Issue.record("Expected .idle phase for signed-in empty favorite input, got \(model.phase)")
            return
        }
    }

    private func makeClient(
        favoriteResponse: Components.Schemas.FavoriteListResponse,
        showResponses: [String: Components.Schemas.ShowSearchResponse]
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
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
        let encoder = APIMockEncoder.make()

        switch operationID {
        case "getFavorites":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(favoriteResponse))
            )
        case "getHomeFeed":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(Components.Schemas.HomeFeedResponse(data: emptyHomeFeed)))
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

    private var emptyHomeFeed: Components.Schemas.HomeFeed {
        .init(
            hero: .init(zipCode: nil, city: nil, state: nil, shows: []),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [],
            moreNearYou: [],
            trendingThisWeek: [],
            popularClubs: []
        )
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
