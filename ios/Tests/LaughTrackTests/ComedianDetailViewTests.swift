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
                    upcomingRunsResponse: .success(
                        .init(
                            data: [
                                fallbackRun(showIDs: [301])
                            ]
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
                    upcomingRunsResponse: .success(.init(data: [])),
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
                    upcomingRunsResponse: .success(.init(data: [])),
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
                    upcomingRunsResponse: .status(.internalServerError),
                    coBillResponse: .success(.init(data: []))
                ),
                authManager: authManager
            )
        )
        await host.settle()

        try host.requireLabel("Mark Normand")
        try host.requireLabel("LaughTrack hit a server error while loading related shows.")
    }

    @Test("related comedians are ranked by shared bill frequency and capped")
    func relatedComediansAreRankedByFrequency() {
        let headliner = DemoContent.primaryComedian
        let firstSeenLowCount = makeLineup(name: "First Seen", uuid: "first-seen", id: 201)
        let firstSeenHighCount = makeLineup(name: "First High", uuid: "first-high", id: 202)
        let secondSeenHighCount = makeLineup(name: "Second High", uuid: "second-high", id: 203)
        let thirdSeenHighCount = makeLineup(name: "Third High", uuid: "third-high", id: 204)
        let fourthSeenHighCount = makeLineup(name: "Fourth High", uuid: "fourth-high", id: 205)
        let cappedOut = makeLineup(name: "Capped Out", uuid: "capped-out", id: 206)

        let shows = [
            showWithLineup(id: 401, lineup: [headliner.asLineup, firstSeenLowCount, firstSeenHighCount, secondSeenHighCount]),
            showWithLineup(id: 402, lineup: [headliner.asLineup, firstSeenHighCount, thirdSeenHighCount]),
            showWithLineup(id: 403, lineup: [headliner.asLineup, secondSeenHighCount, thirdSeenHighCount, fourthSeenHighCount]),
            showWithLineup(id: 404, lineup: [headliner.asLineup, fourthSeenHighCount, cappedOut]),
        ]

        let ranked = ComedianRelatedPresentation.rankedRelatedComedians(
            candidates: [cappedOut, firstSeenLowCount, fourthSeenHighCount, thirdSeenHighCount, secondSeenHighCount, firstSeenHighCount],
            shows: shows,
            currentComedianUUID: headliner.uuid
        )

        #expect(ranked.map(\.uuid) == [
            "first-high",
            "second-high",
            "third-high",
            "fourth-high",
            "first-seen",
        ])
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
        upcomingRunsResponse: MockComedianDetailTransport.EntityResponse<Components.Schemas.UpcomingRunResponse>,
        coBillResponse: MockComedianDetailTransport.EntityResponse<Operations.GetComedianCoBill.Output.Ok.Body.JsonPayload>
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockComedianDetailTransport(
                comedianResponse: comedianResponse,
                upcomingRunsResponse: upcomingRunsResponse,
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

    private func makeLineup(name: String, uuid: String, id: Int) -> Components.Schemas.ComedianLineup {
        .init(
            name: name,
            imageUrl: "https://example.com/\(uuid).png",
            uuid: uuid,
            id: id,
            userId: nil,
            socialData: .init(
                id: id,
                instagramAccount: nil,
                instagramFollowers: nil,
                tiktokAccount: nil,
                tiktokFollowers: nil,
                youtubeAccount: nil,
                youtubeFollowers: nil,
                website: nil,
                popularity: nil,
                linktree: nil
            ),
            isFavorite: false,
            showCount: 1
        )
    }

    private func showWithLineup(id: Int, lineup: [Components.Schemas.ComedianLineup]) -> Components.Schemas.Show {
        var show = fallbackShow(id: id)
        show.lineup = lineup
        return show
    }

    private func fallbackRun(showIDs: [Int], clubID: Int = 101, clubName: String = "Comedy Cellar") -> Components.Schemas.UpcomingRun {
        .init(
            clubID: clubID,
            clubName: clubName,
            clubImageUrl: "https://example.com/show.png",
            shows: showIDs.map { fallbackShow(id: $0, clubID: clubID, clubName: clubName) }
        )
    }
}

private extension Components.Schemas.ComedianDetail {
    var asLineup: Components.Schemas.ComedianLineup {
        .init(
            name: name,
            imageUrl: imageUrl,
            uuid: uuid,
            id: id,
            userId: nil,
            socialData: socialData,
            isFavorite: false,
            showCount: nil
        )
    }
}

private struct MockComedianDetailTransport: ClientTransport {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
    }

    let comedianResponse: EntityResponse<Operations.GetComedian.Output.Ok.Body.JsonPayload>
    let upcomingRunsResponse: EntityResponse<Components.Schemas.UpcomingRunResponse>
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
        case "getComedianUpcomingRuns":
            return try encodedResponse(for: upcomingRunsResponse)
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

#endif
