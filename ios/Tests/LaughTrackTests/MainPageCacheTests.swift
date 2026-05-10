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
        let zipCode = uniqueCacheKey("test-cache-before-network")
        let cache = DataCache<LaughTrackCacheKey>()
        await cache.set(homeFeed(showID: 701), forKey: .homeFeed(zipCode: zipCode))
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 999)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil
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
        let zipCode = uniqueCacheKey("test-cache-after-miss")
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 702)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil
        )

        let cached: Components.Schemas.HomeFeed? = await cache.get(forKey: .homeFeed(zipCode: zipCode))
        #expect(cached?.showsTonight.map(\.id) == [702])
        #expect(transport.requestCount == 1)
    }

    @Test("home rail refreshes after cached data expires")
    func homeRailRefreshesAfterCacheExpiry() async throws {
        let zipCode = uniqueCacheKey("test-cache-expiry")
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 703)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            cacheTTL: 0.05,
            persistentCache: nil
        )
        transport.result = .success(homeFeed(showID: 704))
        try await Task.sleep(for: .milliseconds(100))
        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            cacheTTL: 0.05,
            persistentCache: nil
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
        let zipCode = uniqueCacheKey("test-cache-fallback")
        let cache = DataCache<LaughTrackCacheKey>()
        await cache.set(homeFeed(showID: 705), forKey: .homeFeed(zipCode: zipCode))
        let transport = CountingHomeFeedTransport(result: .failure(URLError(.notConnectedToInternet)))
        let model = HomeShowsTonightModel()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil
        )

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected valid cached data to survive a failing transport")
            return
        }
        #expect(shows.map(\.id) == [705])
        #expect(transport.requestCount == 0)
    }

    @Test("home feed persistent cache survives a new store instance")
    func persistentHomeFeedCacheSurvivesNewStoreInstance() async throws {
        let directory = try temporaryDirectory()
        let writer = PersistentMainPageCache(directory: directory)
        await writer.setHomeFeed(homeFeed(showID: 706), zipCode: "10801", ttl: 60)

        let reader = PersistentMainPageCache(directory: directory)
        let cached = await reader.getHomeFeed(zipCode: "10801")

        #expect(cached?.showsTonight.map(\.id) == [706])
    }

    @Test("main page cache reads home feed from persistent storage after memory miss")
    func mainPageCacheReadsPersistentHomeFeedAfterMemoryMiss() async throws {
        let directory = try temporaryDirectory()
        let persistentCache = PersistentMainPageCache(directory: directory)
        await persistentCache.setHomeFeed(homeFeed(showID: 707), zipCode: "10801", ttl: 60)

        let cache = DataCache<LaughTrackCacheKey>()
        let cached: Components.Schemas.HomeFeed? = await MainPageCache.get(
            .homeFeed(zipCode: "10801"),
            from: cache,
            persistentCache: persistentCache
        )

        #expect(cached?.showsTonight.map(\.id) == [707])
    }

    @Test("home feed persistent cache expires entries")
    func persistentHomeFeedCacheExpiresEntries() async throws {
        let directory = try temporaryDirectory()
        let persistentCache = PersistentMainPageCache(directory: directory)
        await persistentCache.setHomeFeed(homeFeed(showID: 708), zipCode: nil, ttl: 0.05)

        try await Task.sleep(for: .milliseconds(100))
        let cached = await persistentCache.getHomeFeed(zipCode: nil)

        #expect(cached == nil)
    }

    @Test("favorite shows persistent cache survives a new store instance")
    func persistentFavoriteShowsCacheSurvivesNewStoreInstance() async throws {
        let directory = try temporaryDirectory()
        let writer = PersistentMainPageCache(directory: directory)
        await writer.setFavoriteShows([homeShow(id: 709)], requestKey: "comedian-a", ttl: 60)

        let reader = PersistentMainPageCache(directory: directory)
        let cached = await reader.getFavoriteShows(requestKey: "comedian-a")

        #expect(cached?.map(\.id) == [709])
    }

    @Test("init purges orphaned nearby-shows cache files left behind by TASK-1887 removal")
    func initPurgesOrphanedNearbyShowsFiles() async throws {
        let directory = try temporaryDirectory()
        let fm = FileManager.default
        let orphanA = directory.appendingPathComponent("nearby-shows-10801-25.json")
        let orphanB = directory.appendingPathComponent("nearby-shows-default-50.json")
        let keepHomeFeed = directory.appendingPathComponent("home-feed-10801.json")
        let keepUnrelated = directory.appendingPathComponent("nearby-shows-readme.txt")
        try Data("orphan".utf8).write(to: orphanA)
        try Data("orphan".utf8).write(to: orphanB)
        try Data("keep".utf8).write(to: keepHomeFeed)
        try Data("keep".utf8).write(to: keepUnrelated)

        _ = PersistentMainPageCache(directory: directory)

        #expect(!fm.fileExists(atPath: orphanA.path))
        #expect(!fm.fileExists(atPath: orphanB.path))
        #expect(fm.fileExists(atPath: keepHomeFeed.path))
        #expect(fm.fileExists(atPath: keepUnrelated.path))
    }
}

private func temporaryDirectory() throws -> URL {
    let directory = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    return directory
}

private func uniqueCacheKey(_ prefix: String) -> String {
    "\(prefix)-\(UUID().uuidString)"
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
        clubID: 301,
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
                "clubID": \(show.clubID),
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
