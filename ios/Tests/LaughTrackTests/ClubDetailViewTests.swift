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

@Suite("Club detail view", .disabled("TASK-1761: HostedView UI assertions need refresh — see TASK-1740 follow-up"))
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

        try host.requireView(withIdentifier: LaughTrackViewTestID.clubDetailScreen)
        try host.requireLabel("Comedy Cellar")
        try host.requireLabel("What’s on at this room")
        try host.requireLabel("Artists on upcoming bills")
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

        try host.requireLabel("This club could not be found.")
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

        try host.requireLabel("No upcoming shows are available for this club right now.")
        try host.requireLabel("No featured comedians are available for this club yet.")
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

        try host.requireLabel("Comedy Cellar")
        try host.requireLabel("LaughTrack hit a server error while loading this club’s related content.")
    }

    private func makeView(apiClient: Client, authManager: AuthManager) -> some View {
        ClubDetailView(clubID: 201, apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
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

private struct MockClubDetailTransport: ClientTransport {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
    }

    let clubResponse: EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>
    let relatedShowsResponse: EntityResponse<Components.Schemas.ShowSearchResponse>

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
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            return (
                HTTPResponse(
                    status: status,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody("{}")
            )
        }
    }
}
#endif
