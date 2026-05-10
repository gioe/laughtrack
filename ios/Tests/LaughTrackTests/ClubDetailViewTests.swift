#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
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
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    clubResponse: .success(.init(data: primaryClub)),
                    relatedShowsResponse: .success(.init(data: relatedShows, total: relatedShows.count, filters: [], zipCapTriggered: false))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.clubDetailScreen)
        try host.requireLabel("Comedy Cellar")
        try host.requireLabel("Sort: Earliest")
        try host.requireLabel("Comedian")
        try host.requireLabel("Today")
        try host.requireLabel("Mark Normand")
        #expect(host.findText("Location") == nil)
        #expect(host.findText("Use date range") == nil)
        #expect(host.findText("Club detail") == nil)
        #expect(host.findText("8 upcoming") == nil)
        #expect(host.findText("Address on file") == nil)
        host.scrollDown()
        #expect(host.findText("Artists on upcoming bills") == nil)
        #expect(host.findText("Club") == nil)
    }

    @Test("club detail places venue actions in the hero")
    func clubDetailPlacesVenueActionsInHero() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-actions-inline")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    clubResponse: .success(.init(data: primaryClub)),
                    relatedShowsResponse: .success(.init(data: relatedShows, total: relatedShows.count, filters: [], zipCapTriggered: false))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("Website")
        try host.requireLabel("Maps")
        #expect(host.findText("Club details") == nil)
        #expect(host.findText("Venue") == nil)
        #expect(host.findText("Address") == nil)
        #expect(host.findText("117 MacDougal St, New York, NY") == nil)
        #expect(host.findText("ZIP") == nil)
        #expect(host.findText("10012") == nil)
        #expect(host.findText("Visit website") == nil)
        #expect(host.findText("Open in Maps") == nil)
        #expect(host.findText("Take the next step") == nil)
    }

    @Test("club detail surfaces API failures explicitly")
    func clubDetailShowsErrorState() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    clubResponse: .status(.notFound),
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        // LoadFailure.unexpected(status:) renders as "<message> (HTTP <status>)" via
        // LoadFailure.message — the suffix is part of every documented-status error
        // surface, not just this one.
        try host.requireLabel("This club could not be found. (HTTP 404)")
    }

    @Test("club detail renders explicit empty states for missing related content")
    func clubDetailShowsEmptyStates() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    clubResponse: .success(.init(data: primaryClub)),
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("No shows are available right now.")
        host.scrollDown()
        #expect(host.findText("No featured comedians are available for this club yet.") == nil)
    }

    @Test("club detail keeps venue content visible when related shows fail")
    func clubDetailShowsRelatedContentWarning() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-related-warning")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    clubResponse: .success(.init(data: primaryClub)),
                    relatedShowsResponse: .status(.internalServerError)
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("Comedy Cellar")
        try host.requireLabel("mock (HTTP 500)")
    }

    @Test("club detail show search pins requests to the current club")
    func clubDetailShowSearchPinsRequestsToCurrentClub() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-pinned-search")
        let transport = MockClubDetailTransport(
            clubResponse: .success(.init(data: primaryClub)),
            relatedShowsResponse: .success(.init(data: relatedShows, total: relatedShows.count, filters: [], zipCapTriggered: false))
        )
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let host = HostedView(makeView(apiClient: apiClient, authManager: authManager))
        await host.settle()

        #expect(transport.searchShowPaths.contains { path in
            path.contains("club=Comedy%20Cellar")
        })
    }

    private func makeView(apiClient: Client, authManager: AuthManager) -> some View {
        ClubDetailView(clubID: 201, apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "club-detail"))
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(ComedianFavoriteStore())
            .environmentObject(authManager)
    }

    private func makeClient(
        clubResponse: MockClubDetailTransport.EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>,
        relatedShowsResponse: MockClubDetailTransport.EntityResponse<Components.Schemas.ShowSearchResponse>
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockClubDetailTransport(
                clubResponse: clubResponse,
                relatedShowsResponse: relatedShowsResponse
            )
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
#endif
