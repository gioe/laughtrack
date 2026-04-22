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

@Suite("Comedian detail view")
@MainActor
struct ComedianDetailViewTests {
    @Test("comedian detail loads live profile and related content")
    func comedianDetailLoadsAndDisplaysSections() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-success")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                    relatedShowsResponse: .success(
                        .init(
                            data: [
                                DemoContent.showDetailResponse(id: 301)?.data.asShow() ?? fallbackShow(id: 301)
                            ],
                            total: 1,
                            filters: []
                        )
                    )
                ),
                authManager: authManager
            )
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.comedianDetailScreen)
        try host.requireLabel("Mark Normand")
        try host.requireLabel("Catch them live")
        try host.requireLabel("People sharing the bill")
    }

    @Test("comedian detail surfaces API failures explicitly")
    func comedianDetailShowsErrorState() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-error")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    comedianResponse: .status(.notFound),
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: []))
                ),
                authManager: authManager
            )
        )

        try host.requireLabel("This comedian could not be found.")
    }

    @Test("comedian detail renders explicit empty states for missing related content")
    func comedianDetailShowsEmptyStates() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: []))
                ),
                authManager: authManager
            )
        )

        try host.requireLabel("No upcoming shows are available for this comedian right now.")
        try host.requireLabel("No related comedians are available yet.")
    }

    @Test("comedian detail keeps profile content visible when related shows fail")
    func comedianDetailShowsRelatedContentWarning() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-related-warning")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                    relatedShowsResponse: .status(.internalServerError)
                ),
                authManager: authManager
            )
        )

        try host.requireLabel("Mark Normand")
        try host.requireLabel("LaughTrack hit a server error while loading related shows.")
    }

    private func makeView(apiClient: Client, authManager: AuthManager) -> some View {
        ComedianDetailView(comedianID: 101, apiClient: apiClient)
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(ComedianFavoriteStore())
            .environmentObject(authManager)
    }

    private func makeClient(
        comedianResponse: MockComedianDetailTransport.EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>,
        relatedShowsResponse: MockComedianDetailTransport.EntityResponse<Components.Schemas.ShowSearchResponse>
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockComedianDetailTransport(
                comedianResponse: comedianResponse,
                relatedShowsResponse: relatedShowsResponse
            )
        )
    }

    private func fallbackShow(id: Int) -> Components.Schemas.Show {
        .init(
            id: id,
            clubName: "Comedy Cellar",
            date: Date().addingTimeInterval(60 * 60 * 24),
            tickets: nil,
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: [
                .init(
                    name: "Mark Normand",
                    imageUrl: DemoContent.primaryComedian.imageUrl,
                    uuid: DemoContent.primaryComedian.uuid,
                    id: DemoContent.primaryComedian.id,
                    userId: nil,
                    socialData: DemoContent.primaryComedian.socialData,
                    isFavorite: false,
                    showCount: 12
                ),
                .init(
                    name: "Atsuko Okatsuka",
                    imageUrl: "https://example.com/atsuko.png",
                    uuid: "demo-comedian-102",
                    id: 102,
                    userId: nil,
                    socialData: .init(
                        id: 2,
                        instagramAccount: "atsukocomedy",
                        instagramFollowers: 10,
                        tiktokAccount: nil,
                        tiktokFollowers: nil,
                        youtubeAccount: nil,
                        youtubeFollowers: nil,
                        website: nil,
                        popularity: nil,
                        linktree: nil
                    ),
                    isFavorite: false,
                    showCount: 5
                )
            ],
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: nil,
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: 2.0
        )
    }
}

private struct MockComedianDetailTransport: ClientTransport {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
    }

    let comedianResponse: EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>
    let relatedShowsResponse: EntityResponse<Components.Schemas.ShowSearchResponse>

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        switch operationID {
        case "getComedian":
            return try encodedResponse(for: comedianResponse)
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

private extension Components.Schemas.ShowDetail {
    func asShow() -> Components.Schemas.Show {
        .init(
            id: id,
            clubName: club.name,
            date: date,
            tickets: tickets,
            name: name,
            socialData: socialData,
            lineup: lineup,
            description: description,
            address: address,
            room: room,
            imageUrl: imageUrl,
            soldOut: soldOut,
            distanceMiles: distanceMiles
        )
    }
}
#endif
