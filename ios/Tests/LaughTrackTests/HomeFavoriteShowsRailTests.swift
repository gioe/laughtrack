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
    @Test("followed-comedian rail is fail-soft, featured, and detail-linked")
    func followedComedianRailPresentationContract() throws {
        let source = try String(contentsOf: followedComedianRailSourceURL(), encoding: .utf8)

        #expect(source.contains("if case .success(let shows) = model.phase, !shows.isEmpty"))
        #expect(source.contains("HomeFeaturedShowsCarousel("))
        #expect(source.contains("HomeFeaturedShowCarouselItem("))
        #expect(source.contains("show: show"))
        #expect(source.contains("preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredFavoriteHeadlinerID("))
        #expect(source.contains("accessibilityIdentifier: LaughTrackViewTestID.homeFavoriteShowButton(show.id)"))
        #expect(!source.contains("LaughTrackButton(\"See"))
        #expect(!source.contains("FailureCard("))
        #expect(!source.contains("ShowsListSkeleton("))
    }

    @Test("followed-comedian rail consumes the personalized home-feed section")
    func followedComedianRailConsumesHomeFeedSection() async throws {
        let apiClient = makeClient(
            favoriteResponse: .init(data: []),
            showResponses: [:],
            homeFeed: homeFeed(followedComedianShows: [favoriteShow])
        )
        let model = HomeFollowedComedianShowsModel()

        await model.refresh(
            apiClient: apiClient,
            zipCode: "10012",
            distanceMiles: 25,
            cache: nil,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case let .success(shows) = model.phase else {
            Issue.record("Expected .success phase, got \(model.phase)")
            return
        }
        #expect(shows.map(\.id) == [favoriteShow.id])
    }

    @Test("an empty followed-comedian feed remains an omittable successful rail")
    func emptyFollowedComedianFeedIsOmittable() async throws {
        let apiClient = makeClient(
            favoriteResponse: .init(data: []),
            showResponses: [:],
            homeFeed: homeFeed(followedComedianShows: [])
        )
        let model = HomeFollowedComedianShowsModel()

        await model.refresh(
            apiClient: apiClient,
            zipCode: nil,
            cache: nil,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case let .success(shows) = model.phase else {
            Issue.record("Expected .success phase, got \(model.phase)")
            return
        }
        #expect(shows.isEmpty)
    }

    @Test("personalized feed identity follows the authenticated session")
    func personalizedFeedIdentityFollowsAuthenticatedSession() {
        let model = HomeFollowedComedianShowsModel()

        let first = model.requestKey(
            for: "10012",
            distanceMiles: 25,
            sessionDiscriminator: "session-a"
        )
        let second = model.requestKey(
            for: "10012",
            distanceMiles: 25,
            sessionDiscriminator: "session-b"
        )

        #expect(first != second)
    }

    @Test("personalized rail bypasses an unscoped cached home feed")
    func personalizedRailBypassesUnscopedCachedHomeFeed() async throws {
        let cache = DataCache<LaughTrackCacheKey>()
        await cache.set(
            homeFeed(followedComedianShows: [favoriteShow]),
            forKey: .homeFeed(zipCode: "10012", distanceMiles: 25)
        )
        let apiClient = makeClient(
            favoriteResponse: .init(data: []),
            showResponses: [:],
            homeFeed: homeFeed(followedComedianShows: [])
        )
        let model = HomeFollowedComedianShowsModel()

        await model.refresh(
            apiClient: apiClient,
            zipCode: "10012",
            distanceMiles: 25,
            sessionDiscriminator: "session-b",
            cache: cache,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case let .success(shows) = model.phase else {
            Issue.record("Expected .success phase, got \(model.phase)")
            return
        }
        #expect(shows.isEmpty)
    }

    private func makeClient(
        favoriteResponse: Components.Schemas.FavoriteListResponse,
        showResponses: [String: Components.Schemas.ShowSearchResponse],
        homeFeed: Components.Schemas.HomeFeed? = nil
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: MockHomeFavoriteShowsTransport(
                favoriteResponse: favoriteResponse,
                showResponses: showResponses,
                homeFeed: homeFeed ?? self.homeFeed(followedComedianShows: [])
            )
        )
    }

    private func followedComedianRailSourceURL(filePath: String = #filePath) -> URL {
        URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Sources/LaughTrackApp/Home/Views/Rails/HomeFollowedComedianShowsRail.swift")
    }

    private func homeFeed(
        followedComedianShows: [Components.Schemas.Show]
    ) -> Components.Schemas.HomeFeed {
        .init(
            hero: .init(zipCode: nil, city: nil, state: nil, shows: []),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [],
            moreNearYou: [],
            trendingThisWeek: [],
            followedComedianShows: followedComedianShows,
            trendingPodcasts: [],
            popularClubs: []
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
            clubId: 202,
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
    let homeFeed: Components.Schemas.HomeFeed

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
                HTTPBody(try encoder.encode(Components.Schemas.HomeFeedResponse(data: homeFeed)))
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
