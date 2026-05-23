import Foundation
import Testing
import HTTPTypes
import OpenAPIRuntime
import LaughTrackAPIClient
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
        "episodeCount": 0
      },
      "episodes": [],
      "relatedComedians": [\(comedians)]
    }
    """
}

private func makeHomeFeedJSON(showsTonight: [LoaderTestShow]) -> String {
    let shows = showsTonight.map { show in
        let lineup = show.lineupIDs.map { id in
            """
            {"name":"Comic \(id)","imageUrl":"https://example.com/c\(id).jpg","uuid":"comic-\(id)","id":\(id)}
            """
        }.joined(separator: ",")
        return """
        {
          "id": \(show.id),
          "clubId": 301,
          "clubName": "\(show.clubName)",
          "date": "2026-05-23T20:00:00.000Z",
          "imageUrl": "https://example.com/show-\(show.id).png",
          "lineup": [\(lineup)]
        }
        """
    }.joined(separator: ",")
    return """
    {
      "data": {
        "hero": { "zipCode": "10012", "city": "NYC", "state": "NY", "shows": [] },
        "trendingComedians": [],
        "comediansNearYou": [],
        "showsTonight": [\(shows)],
        "moreNearYou": [],
        "trendingThisWeek": [],
        "trendingPodcasts": [],
        "popularClubs": []
      }
    }
    """
}

private func makeClient(homeFeedJSON: String) -> Client {
    let transport = StubClientTransport { _, _, _, operationID in
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

/// Test-only URLProtocol that serves a fixed JSON body for every request. The
/// suite is `.serialized` so the shared `handler` static is not raced across
/// concurrent test cases. Each test calls `makeSession(json:)` immediately
/// before issuing its load, so the handler stays bound to that test's payload.
private final class StubURLProtocol: URLProtocol {
    nonisolated(unsafe) static var handler: (@Sendable (URLRequest) -> (HTTPURLResponse, Data))?

    static func makeSession(json: String) -> URLSession {
        handler = { request in
            let url = request.url ?? URL(string: "https://stub.invalid")!
            let response = HTTPURLResponse(
                url: url,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (response, Data(json.utf8))
        }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return URLSession(configuration: configuration)
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = Self.handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        let (response, data) = handler(request)
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}
