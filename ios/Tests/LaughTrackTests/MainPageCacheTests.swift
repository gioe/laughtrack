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
        await cache.set(homeFeed(showID: 701), forKey: .homeFeed(zipCode: zipCode, distanceMiles: nil))
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 999)))
        let model = HomeShowsTonightModel()
        let coalescer = HomeFeedRequestCoalescer()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
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
        let coalescer = HomeFeedRequestCoalescer()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )

        let cached: Components.Schemas.HomeFeed? = await cache.get(forKey: .homeFeed(zipCode: zipCode, distanceMiles: nil))
        #expect(cached?.showsTonight.map(\.id) == [702])
        #expect(transport.requestCount == 1)
    }

    @Test("home rail refreshes after cached data expires")
    func homeRailRefreshesAfterCacheExpiry() async throws {
        let zipCode = uniqueCacheKey("test-cache-expiry")
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(result: .success(homeFeed(showID: 703)))
        let model = HomeShowsTonightModel()
        let coalescer = HomeFeedRequestCoalescer()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            cacheTTL: 0.05,
            persistentCache: nil,
            coalescer: coalescer
        )
        transport.result = .success(homeFeed(showID: 704))
        try await Task.sleep(for: .milliseconds(100))
        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            cacheTTL: 0.05,
            persistentCache: nil,
            coalescer: coalescer
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
        await cache.set(homeFeed(showID: 705), forKey: .homeFeed(zipCode: zipCode, distanceMiles: nil))
        let transport = CountingHomeFeedTransport(result: .failure(URLError(.notConnectedToInternet)))
        let model = HomeShowsTonightModel()
        let coalescer = HomeFeedRequestCoalescer()

        await model.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
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
            .homeFeed(zipCode: "10801", distanceMiles: nil),
            from: cache,
            persistentCache: persistentCache
        )

        #expect(cached?.showsTonight.map(\.id) == [707])
    }

    @Test("memory and persistent home feed caches retain only public rails")
    func homeFeedCachesRetainOnlyPublicRails() async throws {
        let directory = try temporaryDirectory()
        let persistentCache = PersistentMainPageCache(directory: directory)
        let cache = DataCache<LaughTrackCacheKey>()
        let key = LaughTrackCacheKey.homeFeed(zipCode: "10801", distanceMiles: 25)
        let personalizedFeed = homeFeed(showID: 733, followedShowIDs: [734])

        await MainPageCache.set(
            personalizedFeed,
            forKey: key,
            in: cache,
            persistentCache: persistentCache
        )

        let memoryValue: Components.Schemas.HomeFeed? = await cache.get(forKey: key)
        let diskValue = await PersistentMainPageCache(directory: directory).getHomeFeed(
            zipCode: "10801",
            distanceMiles: 25
        )
        #expect(memoryValue?.showsTonight.map(\.id) == [733])
        #expect(memoryValue?.followedComedianShows.isEmpty == true)
        #expect(diskValue?.showsTonight.map(\.id) == [733])
        #expect(diskValue?.followedComedianShows.isEmpty == true)

        // Defensive reads also sanitize a raw value written outside MainPageCache.
        await cache.set(personalizedFeed, forKey: key)
        let sanitizedRead: Components.Schemas.HomeFeed? = await MainPageCache.get(
            key,
            from: cache,
            persistentCache: persistentCache
        )
        #expect(sanitizedRead?.showsTonight.map(\.id) == [733])
        #expect(sanitizedRead?.followedComedianShows.isEmpty == true)
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

    @Test("home feed written by a prior build version is treated as a miss and deleted")
    func persistentHomeFeedInvalidatesOnSchemaVersionMismatch() async throws {
        let directory = try temporaryDirectory()
        let writer = PersistentMainPageCache(directory: directory, schemaVersion: "build-1")
        await writer.setHomeFeed(homeFeed(showID: 730), zipCode: "10801", ttl: 60)

        // A later build reads the same on-disk directory with a new version.
        let reader = PersistentMainPageCache(directory: directory, schemaVersion: "build-2")
        let cached = await reader.getHomeFeed(zipCode: "10801")
        #expect(cached == nil)

        // The stale entry is deleted, so a same-version writer starts clean.
        let file = directory.appendingPathComponent("home-feed-10801.json")
        #expect(!FileManager.default.fileExists(atPath: file.path))
    }

    @Test("a corrupt persisted entry is deleted and reported as a miss")
    func persistentCacheDeletesUndecodableEntry() async throws {
        let directory = try temporaryDirectory()
        let file = directory.appendingPathComponent("home-feed-10801.json")
        try Data("{ this is not a valid entry }".utf8).write(to: file)

        let cache = PersistentMainPageCache(directory: directory)
        let cached = await cache.getHomeFeed(zipCode: "10801")

        #expect(cached == nil)
        #expect(!FileManager.default.fileExists(atPath: file.path))
    }

    @Test("version invalidation applies to every persisted rail family, not just home feed")
    func persistentFavoriteShowsInvalidatesOnSchemaVersionMismatch() async throws {
        let directory = try temporaryDirectory()
        let writer = PersistentMainPageCache(directory: directory, schemaVersion: "build-1")
        await writer.setFavoriteShows([homeShow(id: 731)], requestKey: "comedian-a", ttl: 60)

        let reader = PersistentMainPageCache(directory: directory, schemaVersion: "build-2")
        let cached = await reader.getFavoriteShows(requestKey: "comedian-a")

        #expect(cached == nil)
    }

    @Test("entries written and read under the same version still resolve")
    func persistentCacheResolvesWhenSchemaVersionMatches() async throws {
        let directory = try temporaryDirectory()
        let writer = PersistentMainPageCache(directory: directory, schemaVersion: "build-1")
        await writer.setHomeFeed(homeFeed(showID: 732), zipCode: "10801", ttl: 60)

        let reader = PersistentMainPageCache(directory: directory, schemaVersion: "build-1")
        let cached = await reader.getHomeFeed(zipCode: "10801")

        #expect(cached?.showsTonight.map(\.id) == [732])
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

@Suite("Home feed load coalescing")
@MainActor
struct HomeFeedLoadCoalescingTests {
    @Test("concurrent Discover rails coalesce matching home feed requests")
    func concurrentDiscoverRailsCoalesceMatchingHomeFeedRequests() async {
        let zipCode = uniqueCacheKey("test-cache-coalescing")
        let cache = DataCache<LaughTrackCacheKey>()
        let transport = CountingHomeFeedTransport(
            result: .success(homeFeed(showID: 720)),
            responseDelay: .milliseconds(100)
        )
        let showsModel = HomeShowsTonightModel()
        let comediansModel = HomeTrendingComediansModel()
        let clubsModel = HomePopularClubsModel()
        let client = makeClient(transport)
        // One fresh coalescer shared by the three concurrent rails: keeps the
        // dedupe-to-one-request assertion meaningful while staying isolated
        // from every other test in the process (TASK-2756).
        let coalescer = HomeFeedRequestCoalescer()

        async let showsRefresh: Void = showsModel.refresh(
            apiClient: client,
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )
        async let comediansRefresh: Void = comediansModel.refresh(
            apiClient: client,
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )
        async let clubsRefresh: Void = clubsModel.refresh(
            apiClient: client,
            zipCode: zipCode,
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )

        _ = await (showsRefresh, comediansRefresh, clubsRefresh)

        #expect(transport.requestCount == 1)
    }

    @Test("anonymous cache is reusable while sign-in refreshes personalized content")
    func anonymousCacheDoesNotSatisfyAuthenticatedPersonalization() async {
        let zipCode = uniqueCacheKey("test-anonymous-to-authenticated")
        let cache = DataCache<LaughTrackCacheKey>()
        let key = LaughTrackCacheKey.homeFeed(zipCode: zipCode, distanceMiles: 25)
        await MainPageCache.set(
            homeFeed(showID: 740),
            forKey: key,
            in: cache,
            persistentCache: nil
        )

        let transport = CountingHomeFeedTransport(
            result: .success(homeFeed(showID: 741, followedShowIDs: [742]))
        )
        let followedModel = HomeFollowedComedianShowsModel()
        await followedModel.refresh(
            apiClient: makeClient(transport),
            zipCode: zipCode,
            distanceMiles: 25,
            sessionDiscriminator: "account-a|session-1",
            cache: cache,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )

        guard case .success(let followedShows) = followedModel.phase else {
            Issue.record("Expected authenticated followed shows to load")
            return
        }
        #expect(followedShows.map(\.id) == [742])
        #expect(transport.requestCount == 1)

        let cached: Components.Schemas.HomeFeed? = await cache.get(forKey: key)
        #expect(cached?.showsTonight.map(\.id) == [741])
        #expect(cached?.followedComedianShows.isEmpty == true)

        let publicTransport = CountingHomeFeedTransport(
            result: .failure(URLError(.notConnectedToInternet))
        )
        let publicModel = HomeShowsTonightModel()
        await publicModel.refresh(
            apiClient: makeClient(publicTransport),
            zipCode: zipCode,
            distanceMiles: 25,
            cache: cache,
            persistentCache: nil,
            coalescer: HomeFeedRequestCoalescer()
        )
        guard case .success(let publicShows) = publicModel.phase else {
            Issue.record("Expected public rails to reuse the sanitized cache")
            return
        }
        #expect(publicShows.map(\.id) == [741])
        #expect(publicTransport.requestCount == 0)
    }

    @Test("account switches do not coalesce personalized home feed requests")
    func accountSwitchDoesNotCoalescePersonalizedRequests() async {
        let zipCode = uniqueCacheKey("test-account-switch")
        let cache = DataCache<LaughTrackCacheKey>()
        let coalescer = HomeFeedRequestCoalescer()
        let accountATransport = CountingHomeFeedTransport(
            result: .success(homeFeed(showID: 750, followedShowIDs: [751])),
            responseDelay: .milliseconds(100)
        )
        let accountBTransport = CountingHomeFeedTransport(
            result: .success(homeFeed(showID: 760, followedShowIDs: [761])),
            responseDelay: .milliseconds(100)
        )
        let accountAModel = HomeFollowedComedianShowsModel()
        let accountBModel = HomeFollowedComedianShowsModel()

        async let accountARefresh: Void = accountAModel.refresh(
            apiClient: makeClient(accountATransport),
            zipCode: zipCode,
            distanceMiles: 25,
            sessionDiscriminator: "account-a|session-1",
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )
        async let accountBRefresh: Void = accountBModel.refresh(
            apiClient: makeClient(accountBTransport),
            zipCode: zipCode,
            distanceMiles: 25,
            sessionDiscriminator: "account-b|session-1",
            cache: cache,
            persistentCache: nil,
            coalescer: coalescer
        )
        _ = await (accountARefresh, accountBRefresh)

        guard case .success(let accountAShows) = accountAModel.phase,
              case .success(let accountBShows) = accountBModel.phase else {
            Issue.record("Expected both account-scoped personalized loads to succeed")
            return
        }
        #expect(accountAShows.map(\.id) == [751])
        #expect(accountBShows.map(\.id) == [761])
        #expect(accountATransport.requestCount == 1)
        #expect(accountBTransport.requestCount == 1)

        let cached: Components.Schemas.HomeFeed? = await cache.get(
            forKey: .homeFeed(zipCode: zipCode, distanceMiles: 25)
        )
        #expect(cached?.followedComedianShows.isEmpty == true)
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

private func homeFeed(
    showID: Int,
    followedShowIDs: [Int] = []
) -> Components.Schemas.HomeFeed {
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
        followedComedianShows: followedShowIDs.map(homeShow),
        trendingPodcasts: [],
        popularClubs: []
    )
}

private func homeShow(id: Int) -> Components.Schemas.Show {
    .init(
        id: id,
        clubId: 301,
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
    let responseDelay: Duration?

    init(result: Response, responseDelay: Duration? = nil) {
        self.result = result
        self.responseDelay = responseDelay
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
        if let responseDelay {
            try await Task.sleep(for: responseDelay)
        }

        switch result {
        case .success(let feed):
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try homeFeedJSON(feed))
            )
        case .failure(let error):
            throw error
        }
    }

    // Derive the response body from the struct fixture so adding a non-optional
    // field to HomeFeed can't silently break decoding here (TASK-2307, TASK-2442).
    private func homeFeedJSON(_ feed: Components.Schemas.HomeFeed) throws -> String {
        let envelope = Components.Schemas.HomeFeedResponse(data: feed)
        let data = try APIMockEncoder.make().encode(envelope)
        return String(decoding: data, as: UTF8.self)
    }
}
