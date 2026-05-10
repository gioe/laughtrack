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
                            filters: [],
                            zipCapTriggered: false
                        )
                    ),
                    coBillResponse: .success(
                        .init(data: [fallbackRelatedComedian()])
                    )
                ),
                authManager: authManager
            )
        )
        await host.settle()

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
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false)),
                    coBillResponse: .success(.init(data: []))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("This comedian could not be found. (HTTP 404)")
    }

    @Test("comedian detail renders explicit empty states for missing related content")
    func comedianDetailShowsEmptyStates() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-empty")
        let host = HostedView(
            makeView(
                apiClient: makeClient(
                    comedianResponse: .success(.init(data: DemoContent.primaryComedian)),
                    relatedShowsResponse: .success(.init(data: [], total: 0, filters: [], zipCapTriggered: false)),
                    coBillResponse: .success(.init(data: []))
                ),
                authManager: authManager
            )
        )
        await host.settle()

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
                    relatedShowsResponse: .status(.internalServerError),
                    coBillResponse: .success(.init(data: []))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("Mark Normand")
        try host.requireLabel("LaughTrack hit a server error while loading related shows.")
    }

    @Test("comedian club runs split same-name clubs by club id")
    func comedianClubRunsUseClubIDInsteadOfName() {
        let shows = [
            fallbackShow(id: 1, clubID: 10, clubName: "Comedy House"),
            fallbackShow(id: 2, clubID: 10, clubName: "Comedy House"),
            fallbackShow(id: 3, clubID: 20, clubName: "Comedy House"),
            fallbackShow(id: 4, clubID: 20, clubName: "Comedy House"),
            fallbackShow(id: 5, clubID: 10, clubName: "Comedy House")
        ]

        let runs = ComedianClubRun.runs(from: shows)

        #expect(runs.map(\.clubID) == [10, 20, 10])
        #expect(runs.map { $0.shows.map(\.id) } == [[1, 2], [3, 4], [5]])
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
        relatedShowsResponse: MockComedianDetailTransport.EntityResponse<Components.Schemas.ShowSearchResponse>,
        coBillResponse: MockComedianDetailTransport.EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockComedianDetailTransport(
                comedianResponse: comedianResponse,
                relatedShowsResponse: relatedShowsResponse,
                coBillResponse: coBillResponse
            )
        )
    }

    private func fallbackRelatedComedian() -> Components.Schemas.ComedianLineup {
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
    }

    private func fallbackShow(
        id: Int,
        clubID: Int = 101,
        clubName: String = "Comedy Cellar"
    ) -> Components.Schemas.Show {
        .init(
            id: id,
            clubID: clubID,
            clubName: clubName,
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
    let coBillResponse: EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>

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
        case "getComedianCoBill":
            return try encodedResponse(for: coBillResponse)
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
            // Error responses must conform to ErrorResponse schema (required `error`
            // field) — without it, the OpenAPI client throws and the model falls
            // through to its network catch instead of the documented status branch.
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

private extension Components.Schemas.ShowDetail {
    func asShow() -> Components.Schemas.Show {
        .init(
            id: id,
            clubID: club.id,
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
