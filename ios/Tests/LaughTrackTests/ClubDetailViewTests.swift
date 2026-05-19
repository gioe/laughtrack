import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Club detail view")
@MainActor
struct ClubDetailViewTests {
    @Test("club detail loads live venue data and related content")
    func clubDetailLoadsAndDisplaysSections() async throws {
        let model = ClubDetailModel(clubID: 201)
        let transport = MockClubDetailTransport(
            clubResponse: .success(.init(data: primaryClub)),
            relatedShowsResponse: .success(.init(data: relatedShows, total: relatedShows.count, filters: [], zipCapTriggered: false))
        )
        await model.loadIfNeeded(apiClient: makeClient(transport: transport))

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }

        #expect(content.club.name == "Comedy Cellar")
        #expect(content.upcomingShows.map(\.name) == ["Mark Normand and Friends"])
        #expect(content.featuredComedians.map(\.name) == ["Mark Normand", "Atsuko Okatsuka"])
        #expect(content.relatedContentMessage == nil)
        #expect(transport.searchShowPaths.contains { path in
            path.contains("club=Comedy%20Cellar") && path.contains("sort=date_asc")
        })
    }

    @Test("club detail places venue actions in the hero")
    func clubDetailPlacesVenueActionsInHero() {
        let actions = ClubDetailHeroPresentation.actions(for: primaryClub)

        #expect(actions.map(\.title) == ["Website", "Maps"])
        #expect(actions.map(\.systemImage) == ["arrow.up.right", "map.fill"])
        #expect(actions.allSatisfy { $0.url != nil })
    }

    @Test("club detail surfaces API failures explicitly")
    func clubDetailShowsErrorState() async throws {
        let model = ClubDetailModel(clubID: 201)
        await model.loadIfNeeded(
            apiClient: makeClient(
                clubResponse: .status(.notFound),
                relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false))
            )
        )

        // LoadFailure.unexpected(status:) renders as "<message> (HTTP <status>)" via
        // LoadFailure.message — the suffix is part of every documented-status error
        // surface, not just this one.
        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected failure phase, got \(model.phase)")
            return
        }
        #expect(failure.message == "This club could not be found. (HTTP 404)")
    }

    @Test("club detail renders explicit empty states for missing related content")
    func clubDetailShowsEmptyStates() async throws {
        let model = ClubDetailModel(clubID: 201)
        await model.loadIfNeeded(
            apiClient: makeClient(
                clubResponse: .success(.init(data: primaryClub)),
                relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false))
            )
        )

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }
        #expect(content.upcomingShows.isEmpty)
        #expect(content.featuredComedians.isEmpty)
        #expect(content.relatedContentMessage == nil)
    }

    @Test("club detail keeps venue content visible when related shows fail")
    func clubDetailShowsRelatedContentWarning() async throws {
        let model = ClubDetailModel(clubID: 201)
        await model.loadIfNeeded(
            apiClient: makeClient(
                clubResponse: .success(.init(data: primaryClub)),
                relatedShowsResponse: .status(.internalServerError)
            )
        )

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }
        #expect(content.club.name == "Comedy Cellar")
        #expect(content.relatedContentMessage == "LaughTrack hit a server error while loading this club’s related content.")
    }

    @Test("club detail show search pins requests to the current club")
    func clubDetailShowSearchPinsRequestsToCurrentClub() async throws {
        let model = ClubDetailModel(clubID: 201)
        let transport = MockClubDetailTransport(
            clubResponse: .success(.init(data: primaryClub)),
            relatedShowsResponse: .success(.init(data: relatedShows, total: relatedShows.count, filters: [], zipCapTriggered: false))
        )
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        await model.loadIfNeeded(apiClient: apiClient)

        #expect(transport.searchShowPaths.contains { path in
            path.contains("club=Comedy%20Cellar")
        })
    }

    private func makeClient(
        clubResponse: MockClubDetailTransport.EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>,
        relatedShowsResponse: MockClubDetailTransport.EntityResponse<Components.Schemas.ShowSearchResponse>
    ) -> Client {
        makeClient(
            transport: MockClubDetailTransport(
                clubResponse: clubResponse,
                relatedShowsResponse: relatedShowsResponse
            )
        )
    }

    private func makeClient(transport: MockClubDetailTransport) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
    }

    private var primaryClub: Components.Schemas.ClubDetail {
        .init(
            id: 201,
            name: "Comedy Cellar",
            imageUrl: "https://example.com/club.png",
            website: "https://www.comedycellar.com",
            address: "117 MacDougal St, New York, NY",
            zipCode: "10012",
            phoneNumber: "(212) 254-3480"
        )
    }

    private var relatedShows: [Components.Schemas.Show] {
        [
            .init(
                id: 301,
                clubID: 201,
                clubName: "Comedy Cellar",
                date: Date().addingTimeInterval(60 * 60 * 24),
                tickets: nil,
                name: "Mark Normand and Friends",
                socialData: nil,
                lineup: [
                    .init(
                        name: "Mark Normand",
                        imageUrl: "https://example.com/mark.png",
                        uuid: "demo-comedian-101",
                        id: 101,
                        userId: nil,
                        socialData: nil,
                        isFavorite: false,
                        showCount: 12
                    ),
                    .init(
                        name: "Atsuko Okatsuka",
                        imageUrl: "https://example.com/atsuko.png",
                        uuid: "demo-comedian-102",
                        id: 102,
                        userId: nil,
                        socialData: nil,
                        isFavorite: false,
                        showCount: 6
                    )
                ],
                description: nil,
                address: "117 MacDougal St, New York, NY",
                room: "Main Room",
                imageUrl: "https://example.com/show.png",
                soldOut: false,
                distanceMiles: 2.0
            )
        ]
    }
}

private final class MockClubDetailTransport: ClientTransport, @unchecked Sendable {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
    }

    let clubResponse: EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>
    let relatedShowsResponse: EntityResponse<Components.Schemas.ShowSearchResponse>
    private(set) var searchShowPaths: [String] = []

    init(
        clubResponse: EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>,
        relatedShowsResponse: EntityResponse<Components.Schemas.ShowSearchResponse>
    ) {
        self.clubResponse = clubResponse
        self.relatedShowsResponse = relatedShowsResponse
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "getClub":
            return try encodedResponse(for: clubResponse)
        case "searchShows":
            searchShowPaths.append(request.path ?? "")
            return try encodedResponse(for: relatedShowsResponse)
        default:
            Issue.record("Unexpected operation: \(operationID)")
            return (HTTPResponse(status: .internalServerError), nil)
        }
    }

    private func encodedResponse<Payload: Encodable>(
        for response: EntityResponse<Payload>
    ) throws -> (HTTPResponse, HTTPBody?) {
        switch response {
        case .success(let payload):
            let encoder = APIMockEncoder.make()
            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            // The OpenAPI spec models error responses (404 / 500) with an
            // ErrorResponse body whose `error` field is required. An empty `{}`
            // body fails decoding and the call throws, dropping the model into
            // its network-error branch instead of the documented status branch.
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(#"{"error":"mock"}"#)
            )
        }
    }
}
