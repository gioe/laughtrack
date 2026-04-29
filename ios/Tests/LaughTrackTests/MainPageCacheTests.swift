import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Main page cache")
@MainActor
struct MainPageCacheTests {
    @Test("home rail uses cached feed before making a network request")
    func homeRailUsesCachedFeedBeforeNetwork() async {
        let cache = DataCache<LaughTrackCacheKey>()
        await cache.set(homeFeed(showID: 701), forKey: .homeFeed(zipCode: nil))
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 999)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: nil,
            cache: cache
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected the cached home feed to render")
            return
        }
        #expect(shows.map(\.id) == [701])
        #expect(transport.requestCount == 0)
    }

    @Test("home rail caches network responses after a miss")
    func homeRailCachesNetworkResponseAfterMiss() async {
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 702)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: nil,
            cache: cache
        )

        let cached: Components.Schemas.HomeFeed? = await cache.get(forKey: .homeFeed(zipCode: nil))
        #expect(cached?.showsTonight.map(\.id) == [702])
        #expect(transport.requestCount == 1)
    }

    @Test("home rail refreshes after cached data expires")
    func homeRailRefreshesAfterCacheExpiry() async throws {
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 703)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: nil,
            cache: cache,
            cacheTTL: 0.05
        )
        transport.result = .success(homeFeed(showID: 704))
        try await Task.sleep(for: .milliseconds(100))
        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: nil,
            cache: cache,
            cacheTTL: 0.05
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected the expired feed to refresh successfully")
            return
        }
        #expect(shows.map(\.id) == [704])
        #expect(transport.requestCount == 2)
    }

    @Test("home rail falls back to valid cached data when refresh transport fails")
    func homeRailFallsBackToValidCacheOnRefreshFailure() async {
        let cache = DataCache<LaughTrackCacheKey>()
        await cache.set(homeFeed(showID: 705), forKey: .homeFeed(zipCode: nil))
        let transport = CountingHomeFeedTransport(result: .failure(URLError(.notConnectedToInternet)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: nil,
            cache: cache
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected valid cached data to survive a failing transport")
            return
        }
        #expect(shows.map(\.id) == [705])
        #expect(transport.requestCount == 0)
    }
}

private func makeClient(_ transport: ClientTransport) -> Client {
    Client(
        serverURL: URL(string: "https://test.example.com")!,
        configuration: .laughTrack,
        transport: transport
    )
}

private func homeFeed(showID: Int) -> Components.Schemas.HomeFeed {
    .init(
        hero: .init(
            zipCode: "10012",
            city: "New York",
            state: "NY",
            shows: []
        ),
        trendingComedians: [],
        comediansNearYou: [],
        showsTonight: [homeShow(id: showID)],
        moreNearYou: [],
        trendingThisWeek: [],
        popularClubs: []
    )
}

private func homeShow(id: Int) -> Components.Schemas.Show {
    .init(
        id: id,
        clubName: "New York Comedy Club",
        date: Date().addingTimeInterval(60 * 60),
        tickets: [],
        name: "Cached Show \(id)",
        socialData: nil,
        lineup: [],
        description: "A cached test show.",
        address: "241 E 24th St, New York, NY",
        room: "Main Room",
        imageUrl: "https://example.com/show.png",
        soldOut: false,
        distanceMiles: nil
    )
}

private final class CountingHomeFeedTransport: ClientTransport, @unchecked Sendable {
    enum Response: Sendable {
        case success(Components.Schemas.HomeFeed)
        case failure(any Error)
    }

    private let lock = NSLock()
    var result: Response

    init(result: Response) {
        self.result = result
    }

    var requestCount: Int {
        lock.withLock { count }
    }

    private var count = 0

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        lock.withLock {
            count += 1
        }

        switch result {
        case .success(let feed):
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(homeFeedJSON(feed))
            )
        case .failure(let error):
            throw error
        }
    }

    private func homeFeedJSON(_ feed: Components.Schemas.HomeFeed) -> String {
        let show = feed.showsTonight[0]
        let name = show.name ?? "Cached Show \(show.id)"
        let clubName = show.clubName ?? "New York Comedy Club"
        return """
        {
          "data": {
            "hero": {
              "zipCode": "\(feed.hero.zipCode ?? "")",
              "city": "\(feed.hero.city ?? "")",
              "state": "\(feed.hero.state ?? "")",
              "shows": []
            },
            "trendingComedians": [],
            "comediansNearYou": [],
            "showsTonight": [
              {
                "id": \(show.id),
                "date": "2026-04-29T00:00:00.000Z",
                "name": "\(name)",
                "clubName": "\(clubName)",
                "imageUrl": "\(show.imageUrl)",
                "soldOut": false,
                "lineup": [],
                "tickets": []
              }
            ],
            "moreNearYou": [],
            "trendingThisWeek": [],
            "popularClubs": []
          }
        }
        """
    }
}
