#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Home shows tonight model")
@MainActor
struct HomeShowsTonightModelTests {
    @Test("loads shows tonight without a nearby preference")
    func loadsShowsTonightWithoutNearbyPreference() async {
        let model = HomeShowsTonightModel()

        await model.refresh(apiClient: makeHomeShowsTonightClient(), zipCode: nil)

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

        await model.refresh(apiClient: makeHomeShowsTonightClient(), zipCode: "10012")

        guard case .success(let shows) = model.phase else {
            Issue.record("Expected shows-tonight success phase")
            return
        }

        #expect(shows.map(\.id) == [801, 802, 803])
    }
}

private func makeHomeShowsTonightClient() -> Client {
    Client(
        serverURL: URL(string: "https://example.com")!,
        configuration: .laughTrack,
        transport: MockHomeShowsTonightTransport()
    )
}

private struct MockHomeShowsTonightTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

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
        .init(
            hero: .init(zipCode: "10012", city: "New York", state: "NY", shows: [show(id: 802)]),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [show(id: 801), show(id: 802)],
            moreNearYou: [],
            trendingThisWeek: [show(id: 803), show(id: 801)],
            popularClubs: []
        )
    }

    private func show(id: Int) -> Components.Schemas.Show {
        .init(
            id: id,
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
#endif
