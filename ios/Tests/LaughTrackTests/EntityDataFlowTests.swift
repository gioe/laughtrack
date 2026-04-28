import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Entity data flow")
@MainActor
struct EntityDataFlowTests {
    @Test("entity navigation targets map to the expected app routes")
    func navigationTargetsMapToRoutes() {
        #expect(EntityNavigationTarget.show(7).route == .showDetail(7))
        #expect(EntityNavigationTarget.comedian(8).route == .comedianDetail(8))
        #expect(EntityNavigationTarget.club(9).route == .clubDetail(9))
    }

    @Test("home trending comedians keeps no-photo entries behind ten photo-backed entries")
    func homeTrendingComediansPrioritizesPhotoBackedEntries() {
        let comedians = makeTrendingComedians(photoCount: 10, includesNoPhoto: true)
        let railItems = HomeTrendingComediansModel.railItems(from: comedians)

        #expect(railItems.prefix(10).allSatisfy { !$0.imageUrl.isEmpty })
        #expect(railItems[10].imageUrl.isEmpty)
    }

    @Test("home trending comedians with fewer than ten photos hides no-photo entries")
    func homeTrendingComediansHidesNoPhotoEntriesBeforeFirstPageIsFull() {
        let comedians = makeTrendingComedians(photoCount: 9, includesNoPhoto: true)
        let railItems = HomeTrendingComediansModel.railItems(from: comedians)

        #expect(railItems.count == 9)
        #expect(railItems.allSatisfy { !$0.imageUrl.isEmpty })
    }

    @Test("search model standardizes reload and load more pagination")
    func searchModelReloadAndLoadMore() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "clubs") { page, query in
            #expect(page == 0)
            #expect(query == "clubs")
            return .success(.init(items: [10, 11], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11])
            #expect(page.total == 4)
            #expect(page.page == 0)
        default:
            Issue.record("Expected reload to finish in a success phase")
        }

        await model.loadMore(query: "clubs") { page, query in
            #expect(page == 1)
            #expect(query == "clubs")
            return .success(.init(items: [12, 13], total: 4))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [10, 11, 12, 13])
            #expect(page.total == 4)
            #expect(page.page == 1)
        default:
            Issue.record("Expected loadMore to preserve and append results")
        }
    }

    @Test("search model keeps prior results and surfaces pagination failures")
    func searchModelKeepsResultsOnPaginationFailure() async {
        let model = EntitySearchModel<String, Int>()

        await model.reload(query: "shows") { _, _ in
            .success(.init(items: [1, 2], total: 3))
        }

        await model.loadMore(query: "shows") { _, _ in
            .failure(.network("Timed out"))
        }

        switch model.phase {
        case .success(let page):
            #expect(page.items == [1, 2])
            #expect(page.page == 0)
        default:
            Issue.record("Expected prior success page to remain after pagination failure")
        }

        #expect(model.paginationFailure == .network("Timed out"))
    }

    @Test("failure messages include status codes and classify by case")
    func loadFailureDisplay() {
        #expect(LoadFailure.network("No signal").message == "No signal")
        #expect(LoadFailure.network("No signal").defaultTitle == "No connection")

        #expect(LoadFailure.unauthorized("Session expired").message == "Session expired (HTTP 401)")
        #expect(LoadFailure.unauthorized("Session expired").defaultTitle == "Sign in required")

        #expect(LoadFailure.badParams("Bad date").message == "Bad date (HTTP 400)")

        let server = LoadFailure.serverError(status: 503, message: "Upstream down")
        #expect(server.message == "Upstream down (HTTP 503)")
        #expect(server.defaultTitle == "Server hiccup")

        let serverNoMessage = LoadFailure.serverError(status: 500, message: nil)
        #expect(serverNoMessage.message.contains("HTTP 500"))

        #expect(LoadFailure.unexpected(status: 429, message: "Rate limited").message == "Rate limited (HTTP 429)")
        #expect(LoadFailure.unexpected(status: 0, message: "Local-only note").message == "Local-only note")

        let limited = LoadFailure.rateLimited(retryAfter: nil, message: "Slowing things down.")
        #expect(limited.message == "Slowing things down. Please try again in a moment. (HTTP 429)")
        #expect(limited.defaultTitle == "Too many requests")

        let limitedWithRetry = LoadFailure.rateLimited(retryAfter: 12, message: nil)
        #expect(limitedWithRetry.message == "LaughTrack is busy right now. Please try again in 12 seconds. (HTTP 429)")

        let limitedSingleSecond = LoadFailure.rateLimited(retryAfter: 1, message: nil)
        #expect(limitedSingleSecond.message.contains("1 second."))
    }

    @Test("recovery action routes unauthorized to signIn, everything else to retry")
    func recoveryActionRouting() {
        #expect(LoadFailure.unauthorized("x").recoveryAction == .signIn)
        #expect(LoadFailure.network("y").recoveryAction == .retry)
        #expect(LoadFailure.badParams("z").recoveryAction == .retry)
        #expect(LoadFailure.rateLimited(retryAfter: nil, message: nil).recoveryAction == .retry)
        #expect(LoadFailure.serverError(status: 500, message: nil).recoveryAction == .retry)
        #expect(LoadFailure.unexpected(status: 418, message: nil).recoveryAction == .retry)
    }

    @Test("cancelled reloads do not overwrite phase with failure")
    func cancelledReloadKeepsPhase() async {
        let model = EntitySearchModel<String, Int>()

        let task = Task {
            await model.reload(query: "shows") { _, _ in
                try? await Task.sleep(for: .milliseconds(50))
                return .failure(.network("Simulated cancellation"))
            }
        }
        task.cancel()
        await task.value

        if case .failure = model.phase {
            Issue.record("Cancelled reload must not surface a failure phase")
        }
    }

    @Test("undocumented statuses classify into the right case")
    func classifyUndocumentedMaps() {
        if case .unauthorized = classifyUndocumented(status: 401, context: "shows") {} else {
            Issue.record("401 must map to .unauthorized")
        }
        if case .badParams = classifyUndocumented(status: 400, context: "shows") {} else {
            Issue.record("400 must map to .badParams")
        }
        if case .serverError(let status, _) = classifyUndocumented(status: 502, context: "shows") {
            #expect(status == 502)
        } else {
            Issue.record("5xx must map to .serverError")
        }
        if case .rateLimited = classifyUndocumented(status: 429, context: "shows") {} else {
            Issue.record("429 must map to .rateLimited")
        }
        if case .unexpected(let status, _) = classifyUndocumented(status: 418, context: "shows") {
            #expect(status == 418)
        } else {
            Issue.record("Other statuses must map to .unexpected")
        }
    }

    @Test("show detail surfaces a non-nil retryAfter from the 429 Retry-After header")
    func showDetailRateLimitedExtractsRetryAfterFromHeader() async {
        let transport = StubRateLimitedShowTransport(retryAfter: 12)
        let client = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let model = ShowDetailModel(showID: 301)
        await model.loadIfNeeded(apiClient: client, favorites: ComedianFavoriteStore())

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected ShowDetailModel to surface a failure phase for 429")
            return
        }
        guard case .rateLimited(let retryAfter, _) = failure else {
            Issue.record("Expected .rateLimited failure, got \(failure)")
            return
        }
        #expect(retryAfter == 12)
        #expect(failure.message.contains("Please try again in 12 seconds."))
    }

    @Test("detail model only performs its first automatic load once")
    func detailModelOnlyLoadsOnceWhenIdle() async {
        let model = EntityDetailModel<Int>()
        var callCount = 0

        await model.loadIfNeeded {
            callCount += 1
            return .success(42)
        }

        await model.loadIfNeeded {
            callCount += 1
            return .success(99)
        }

        #expect(callCount == 1)

        switch model.phase {
        case .success(let value):
            #expect(value == 42)
        default:
            Issue.record("Expected detail model to hold onto its first loaded value")
        }
    }
}

private func makeTrendingComedians(
    photoCount: Int,
    includesNoPhoto: Bool
) -> [Components.Schemas.ComedianListItem] {
    let photoBacked = (1...photoCount).map { index in
        Components.Schemas.ComedianListItem(
            id: 1000 + index,
            uuid: "trending-comedian-\(index)",
            name: "Comic \(index)",
            imageUrl: "https://example.com/comic-\(index).jpg",
            socialData: .init(
                id: 2000 + index,
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
            showCount: 11 - index
        )
    }

    guard includesNoPhoto else { return photoBacked }

    return photoBacked + [
        .init(
            id: 2001,
            uuid: "trending-comedian-no-photo",
            name: "No Photo Comic",
            imageUrl: "",
            socialData: .init(
                id: 3001,
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
            showCount: 3
        )
    ]
}

private struct StubRateLimitedShowTransport: ClientTransport {
    let retryAfter: Int

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let response = HTTPResponse(
            status: .tooManyRequests,
            headerFields: [
                .contentType: "application/json",
                .retryAfter: String(retryAfter),
            ]
        )
        return (response, HTTPBody(#"{"error":"slow down"}"#))
    }
}
