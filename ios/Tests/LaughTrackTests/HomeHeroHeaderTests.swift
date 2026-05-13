import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Home shows tonight model")
@MainActor
struct HomeShowsTonightModelTests {
    @Test("loads shows tonight without a nearby preference")
    func loadsShowsTonightWithoutNearbyPreference() async {
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeHomeShowsTonightClient(),
            zipCode: nil,
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: nil
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected shows-tonight success phase")
            return
        }

        #expect(shows.map(\.id) == [801, 802, 803])
        #expect(model.cityTitle == "New York, NY")
    }

    @Test("deduplicates fallback hero and weekly shows behind tonight")
    func deduplicatesFallbackShowsBehindTonight() async {
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeHomeShowsTonightClient(),
            zipCode: "10012",
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: nil
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected shows-tonight success phase")
            return
        }

        #expect(shows.map(\.id) == [801, 802, 803])
    }

    @Test("limits shows tonight to five unique shows")
    func limitsShowsTonightToFiveUniqueShows() async {
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeHomeShowsTonightClient(showIDs: Array(801...808)),
            zipCode: "10013",
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: nil
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected shows-tonight success phase")
            return
        }

        #expect(shows.map(\.id) == [801, 802, 803, 804, 805])
    }

    @Test("see more seed opens the shows near me search")
    func seeMoreSeedOpensShowsNearMeSearch() async {
        let preference = NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 50,
            city: "New York",
            state: "NY"
        )

        #expect(HomeShowsTonightModel.seeMoreSearchSeed(nearbyPreference: preference) == SearchRootModel.Seed(
            pivot: .shows,
            query: "",
            shortcut: "Near Me",
            nearbyPreference: preference
        ))
    }

    @Test("loads nearby preference from the home feed hero")
    func loadsNearbyPreferenceFromHomeFeedHero() async {
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeHomeShowsTonightClient(),
            zipCode: nil,
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: nil
        )

        #expect(model.feedNearbyPreference == NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 25,
            city: "New York",
            state: "NY"
        ))
    }
}

private func makeHomeShowsTonightClient(showIDs: [Int] = [801, 802, 803]) -> Client {
    Client(
        serverURL: URL(string: "https://example.com")!,
        configuration: .laughTrack,
        transport: MockHomeShowsTonightTransport(showIDs: showIDs)
    )
}

private struct MockHomeShowsTonightTransport: ClientTransport {
    let showIDs: [Int]

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = APIMockEncoder.make()

        switch operationID {
        case "getHomeFeed":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(Components.Schemas.HomeFeedResponse(data: homeFeed)))
            )
        default:
            return (
                HTTPResponse(status: .internalServerError, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"unexpected operation"}"#)
            )
        }
    }

    private var homeFeed: Components.Schemas.HomeFeed {
        let feedShows = showIDs.map { show(id: $0) }
        return .init(
            hero: .init(zipCode: "10012", city: "New York", state: "NY", shows: Array(feedShows.dropFirst().prefix(2))),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: Array(feedShows.prefix(4)),
            moreNearYou: [],
            trendingThisWeek: feedShows + Array(feedShows.prefix(1)),
            popularClubs: []
        )
    }

    private func show(id: Int) -> Components.Schemas.Show {
        .init(
            id: id,
            clubID: 201,
            clubName: "Comedy Cellar",
            date: Date().addingTimeInterval(TimeInterval(id - 800) * 60 * 60),
            tickets: [.init(price: 24, purchaseUrl: "https://example.com/tickets/\(id)", soldOut: false, _type: "General admission")],
            name: "Tonight Show \(id)",
            socialData: nil,
            lineup: [],
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show-\(id).png",
            soldOut: false,
            distanceMiles: nil
        )
    }
}
