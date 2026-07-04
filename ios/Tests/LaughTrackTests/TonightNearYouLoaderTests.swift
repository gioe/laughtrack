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
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")])
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match?.hostName == "Mark Normand")
        #expect(match?.show.id == 701)
        #expect(match?.show.clubName == "Comedy Cellar")

        let requestedPath = StubURLProtocol.lastRequest?.url?.path
        #expect(requestedPath == "/api/v1/podcasts/42")
    }

    @Test("only the first related comedian is considered the host")
    func onlyFirstRelatedComedianIsHost() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [
                (id: 999, name: "Other Host"),
                (id: 101, name: "Mark Normand"),
            ])
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("returns nil when no show contains the host")
    func returnsNilWhenHostAbsent() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [(id: 999, name: "Distant Comic")])
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
                .init(id: 702, clubName: "Other Club", lineupIDs: [50]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("returns nil when the showsTonight feed is empty")
    func returnsNilWhenFeedEmpty() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")])
        )
        let client = makeClient(homeFeedJSON: makeHomeFeedJSON(showsTonight: []))

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("returns nil when podcast detail request fails")
    func returnsNilWhenPodcastDetailRequestFails() async {
        let session = StubURLProtocol.makeFailingSession()
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("returns nil when home feed request fails")
    func returnsNilWhenHomeFeedRequestFails() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")])
        )
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: StubClientTransport.alwaysFails()
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("returns nil when the podcast detail has no related comedians")
    func returnsNilWhenDetailHasNoRelatedComedians() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [])
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [42, 101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match == nil)
    }

    @Test("the first matching show wins when the host headlines multiple")
    func firstMatchingShowWins() async {
        let session = StubURLProtocol.makeSession(
            json: makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")])
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "First Show", lineupIDs: [101]),
                .init(id: 702, clubName: "Second Show", lineupIDs: [101]),
                .init(id: 703, clubName: "Third Show", lineupIDs: [101]),
            ])
        )

        let match = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session
        )

        #expect(match?.show.id == 701)
        #expect(match?.show.clubName == "First Show")
    }

    @Test("reuses cached podcast detail and home feed on repeated loads")
    func reusesCachedPodcastDetailAndHomeFeed() async {
        let cache = DataCache<LaughTrackCacheKey>()
        let counter = RequestCounter()
        let session = StubURLProtocol.makeSession(
            handler: { request in
                counter.incrementURLSession()
                let url = request.url ?? URL(string: "https://stub.invalid")!
                let response = HTTPURLResponse(
                    url: url,
                    statusCode: 200,
                    httpVersion: nil,
                    headerFields: ["Content-Type": "application/json"]
                )!
                return (response, Data(makeDetailJSON(relatedComedians: [(id: 101, name: "Mark Normand")]).utf8))
            },
            capturesLastRequest: true
        )
        let client = makeClient(
            homeFeedJSON: makeHomeFeedJSON(showsTonight: [
                .init(id: 701, clubName: "Comedy Cellar", lineupIDs: [101]),
            ]),
            onRequest: {
                counter.incrementAPIClient()
            }
        )

        let first = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session,
            cache: cache
        )
        let second = await TonightNearYouLoader.load(
            podcastID: 42,
            apiClient: client,
            zipCode: "10012",
            urlSession: session,
            cache: cache
        )

        #expect(first?.show.id == 701)
        #expect(second?.show.id == 701)
        #expect(counter.urlSessionRequests == 1)
        #expect(counter.apiClientRequests == 1)
    }
}

private final class RequestCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var urlSessionCount = 0
    private var apiClientCount = 0

    var urlSessionRequests: Int {
        lock.withLock { urlSessionCount }
    }

    var apiClientRequests: Int {
        lock.withLock { apiClientCount }
    }

    func incrementURLSession() {
        lock.withLock { urlSessionCount += 1 }
    }

    func incrementAPIClient() {
        lock.withLock { apiClientCount += 1 }
    }
}

private struct LoaderTestShow {
    let id: Int
    let clubName: String
    let lineupIDs: [Int]
}

private func makeDetailJSON(relatedComedians: [(id: Int, name: String)]) -> String {
    let comedians = relatedComedians.map { comedian in
        """
        {"id":\(comedian.id),"uuid":"comedian-\(comedian.id)","name":"\(comedian.name)","imageUrl":null}
        """
    }.joined(separator: ",")
    return """
    {
      "podcast": {
        "id": 42,
        "title": "Test Pod",
        "authorName": null,
        "websiteUrl": null,
        "feedUrl": null,
        "imageUrl": null,
        "description": null,
        "episodeCount": 0,
        "hosts": []
      },
      "episodes": [],
      "relatedComedians": [\(comedians)]
    }
    """
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

private func makeClient(homeFeedJSON: String, onRequest: (@Sendable () -> Void)? = nil) -> Client {
    let transport = StubClientTransport { _, _, _, operationID in
        onRequest?()
        #expect(operationID == "getHomeFeed")
        return (
            HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
            HTTPBody(homeFeedJSON)
        )
    }
    return Client(
        serverURL: URL(string: "https://test.example.com")!,
        configuration: .laughTrack,
        transport: transport
    )
}
