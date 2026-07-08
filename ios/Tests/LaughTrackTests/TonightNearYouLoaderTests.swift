import Foundation
import Testing
import HTTPTypes
import OpenAPIRuntime
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Tonight near you loader", .serialized)
struct TonightNearYouLoaderTests {
    @Test("returns a match when the host appears in a show's lineup")
    func returnsMatchWhenHostInLineup() async {
        let (client, transport) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match?.hostName == "Mark Normand")
        #expect(match?.show.id == 701)
        #expect(match?.show.clubName == "Comedy Cellar")

        let detailRequest = transport.capturedRequests.first { $0.operationID == "getPodcast" }
        #expect(detailRequest?.path == "/api/v1/podcasts/42")
    }

    @Test("only the first related comedian is considered the host")
    func onlyFirstRelatedComedianIsHost() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [
                (id: 999, name: "Other Host"),
                (id: 101, name: "Mark Normand"),
            ]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("returns nil when no show contains the host")
    func returnsNilWhenHostAbsent() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 999, name: "Distant Comic")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
                .init(id: 702, clubName: "Other Club", lineupIDs: [50]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("returns nil when the showsTonight feed is empty")
    func returnsNilWhenFeedEmpty() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("returns nil when podcast detail request fails")
    func returnsNilWhenPodcastDetailRequestFails() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ]),
            failGetPodcast: true
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("returns nil when home feed request fails")
    func returnsNilWhenHomeFeedRequestFails() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: []),
            failGetHomeFeed: true
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("returns nil when the podcast detail has no related comedians")
    func returnsNilWhenDetailHasNoRelatedComedians() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: []),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match == nil)
    }

    @Test("the first matching show wins when the host headlines multiple")
    func firstMatchingShowWins() async {
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "First Show", lineupIDs: [101]),
                .init(id: 702, clubName: "Second Show", lineupIDs: [101]),
                .init(id: 703, clubName: "Third Show", lineupIDs: [101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012"
        )

        #expect(match?.show.id == 701)
        #expect(match?.show.clubName == "First Show")
    }

    @Test("reuses cached podcast detail and home feed on repeated loads")
    func reusesCachedPodcastDetailAndHomeFeed() async {
        let cache = DataCache<LaughTrackCacheKey>()
        let counter = RequestCounter()
        let (client, _) = makeClient(
            podcastDetailJSON: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]),
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ]),
            onGetPodcast: { counter.incrementPodcast() },
            onGetHomeFeed: { counter.incrementHomeFeed() }
        )

        let first = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            cache: cache
        )
        let second = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            cache: cache
        )

        #expect(first?.show.id == 701)
        #expect(second?.show.id == 701)
        #expect(counter.podcastRequests == 1)
        #expect(counter.homeFeedRequests == 1)
    }
}

private final class RequestCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var podcastCount = 0
    private var homeFeedCount = 0

    var podcastRequests: Int {
        lock.withLock { podcastCount }
    }

    var homeFeedRequests: Int {
        lock.withLock { homeFeedCount }
    }

    func incrementPodcast() {
        lock.withLock { podcastCount += 1 }
    }

    func incrementHomeFeed() {
        lock.withLock { homeFeedCount += 1 }
    }
}

private struct LoaderTestShow {
    let id: Int
    let clubName: String
    let lineupIDs: [Int]
}

// Built from the generated PodcastDetailResponse schema (encoded via
// APIMockEncoder) so adding a non-optional field to the spec can't silently
// break decoding here — the same guard makeHomeFeedJSON already provides.
private func makeDetailJSON(relatedComedians: [(id: Int, name: String)]) -> String {
    let response = Components.Schemas.PodcastDetailResponse(
        podcast: .init(
            id: 42,
            slug: "test-pod",
            title: "Test Pod",
            authorName: nil,
            websiteUrl: nil,
            feedUrl: nil,
            imageUrl: nil,
            description: nil,
            episodeCount: 0,
            hosts: []
        ),
        episodes: [],
        relatedComedians: relatedComedians.map { comedian in
            .init(
                id: comedian.id,
                uuid: "comedian-\(comedian.id)",
                name: comedian.name,
                imageUrl: "https://example.com/\(comedian.id).jpg",
                socialData: .init(id: comedian.id),
                showCount: 0
            )
        }
    )
    let data = try! APIMockEncoder.make().encode(response)
    return String(decoding: data, as: UTF8.self)
}

// Derive the response body from the struct fixture so adding a non-optional
// field to HomeFeed can't silently break decoding here (TASK-2307, TASK-2442).
private func makeHomeFeedJSON(showsTonight: [LoaderTestShow]) -> String {
    let feed = Components.Schemas.HomeFeed(
        hero: .init(zipCode: "10012", city: "NYC", state: "NY", shows: []),
        trendingComedians: [],
        comediansNearYou: [],
        showsTonight: showsTonight.map { show in
            .init(
                id: show.id,
                clubId: 301,
                clubName: show.clubName,
                date: Date().addingTimeInterval(60 * 60),
                lineup: show.lineupIDs.map { id in
                    .init(
                        name: "Comic \(id)",
                        imageUrl: "https://example.com/c\(id).jpg",
                        uuid: "comic-\(id)",
                        id: id
                    )
                },
                imageUrl: "https://example.com/show-\(show.id).png"
            )
        },
        moreNearYou: [],
        trendingThisWeek: [],
        trendingPodcasts: [],
        popularClubs: []
    )
    let envelope = Components.Schemas.HomeFeedResponse(data: feed)
    let data = try! APIMockEncoder.make().encode(envelope)
    return String(decoding: data, as: UTF8.self)
}

/// Builds a Client whose stub transport serves both the podcast-detail
/// (`getPodcast`) and home-feed (`getHomeFeed`) operations, since both now flow
/// through the same generated client (TASK-3631). Returns the transport too so
/// tests can assert on captured requests.
private func makeClient(
    podcastDetailJSON: String,
    homeFeedJSON: String,
    failGetPodcast: Bool = false,
    failGetHomeFeed: Bool = false,
    onGetPodcast: (@Sendable () -> Void)? = nil,
    onGetHomeFeed: (@Sendable () -> Void)? = nil
) -> (Client, StubClientTransport) {
    let transport = StubClientTransport { _, _, _, operationID in
        switch operationID {
        case "getPodcast":
            onGetPodcast?()
            if failGetPodcast { throw URLError(.notConnectedToInternet) }
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(podcastDetailJSON)
            )
        case "getHomeFeed":
            onGetHomeFeed?()
            if failGetHomeFeed { throw URLError(.notConnectedToInternet) }
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(homeFeedJSON)
            )
        default:
            #expect(Bool(false), "unexpected operation \(operationID)")
            return (HTTPResponse(status: .internalServerError), nil)
        }
    }
    let client = Client(
        serverURL: URL(string: "https://test.example.com")!,
        configuration: .laughTrack,
        transport: transport,
        middlewares: [APIVersionPathMiddleware()]
    )
    return (client, transport)
}
