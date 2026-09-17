import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Show detail view")
@MainActor
struct ShowDetailViewTests {
    @Test("show detail model loads live show data for core sections")
    func showDetailModelLoadsCoreSectionState() async throws {
        let model = ShowDetailModel(showID: 301)
        let favorites = ComedianFavoriteStore()

        await model.loadIfNeeded(
            apiClient: makeClient(
                response: .success(
                    DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
                )
            ),
            favorites: favorites
        )

        guard case .success(let response) = model.phase else {
            Issue.record("Expected show detail success phase, got \(model.phase)")
            return
        }

        #expect(response.data.name == "Mark Normand and Friends")
        #expect(response.data.lineup?.map(\.name) == ["Mark Normand", "Atsuko Okatsuka", "Sam Morril"])
        #expect(response.relatedShows.map(\.id) == [302])
        #expect(ShowDetailPresentation.summaryFacts(for: response.data).map(\.label) == ["When", "Venue", "Distance", "Tickets"])
        #expect(favorites.value(for: "demo-comedian-101") == false)
        #expect(favorites.value(for: "demo-comedian-102") == true)
    }

    @Test("show detail model surfaces API failures explicitly")
    func showDetailModelShowsErrorState() async throws {
        let model = ShowDetailModel(showID: 301)

        await model.loadIfNeeded(
            apiClient: makeClient(response: .status(.notFound)),
            favorites: ComedianFavoriteStore()
        )

        guard case .failure(let failure) = model.phase else {
            Issue.record("Expected show detail failure phase, got \(model.phase)")
            return
        }

        #expect(failure.message == "This show could not be found. (HTTP 404)")
    }

    @Test("show detail model keeps empty optional section state explicit")
    func showDetailModelKeepsEmptySectionState() async throws {
        var response = DemoContent.showDetailResponse(id: 302) ?? DemoContent.primaryShowDetail
        response.data.lineup = nil
        response.relatedShows = []
        response.data.tickets = nil
        response.data.cta = .init(url: nil, label: "Buy tickets", isSoldOut: false)
        response.data.showPageUrl = ""
        let model = ShowDetailModel(showID: 301)

        await model.loadIfNeeded(
            apiClient: makeClient(response: .success(response)),
            favorites: ComedianFavoriteStore()
        )

        guard case .success(let loaded) = model.phase else {
            Issue.record("Expected show detail success phase, got \(model.phase)")
            return
        }

        #expect(loaded.data.lineup == nil)
        #expect(loaded.relatedShows.isEmpty)
        #expect(ShowDetailPresentation.summaryFacts(for: loaded.data).first { $0.label == "Tickets" }?.value == "Ticket link unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: loaded.data) == nil)
    }

    @Test("show detail keeps cached content when revalidation fails and reload retries")
    func showDetailLoadIfNeededUsesCacheAndReloadFetches() async throws {
        let cache = DataCache<LaughTrackCacheKey>()
        let recorder = FavoriteOperationRecorder()
        let client = makeClient(
            response: .success(DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail),
            favoriteRecorder: recorder
        )

        let firstModel = ShowDetailModel(showID: 301)
        await firstModel.loadIfNeeded(apiClient: client, favorites: ComedianFavoriteStore(), cache: cache)

        let cachedModel = ShowDetailModel(showID: 301)
        await cachedModel.loadIfNeeded(
            apiClient: makeClient(response: .status(.internalServerError), favoriteRecorder: recorder),
            favorites: ComedianFavoriteStore(),
            cache: cache
        )

        let afterCachedLoadOperations = await recorder.operations
        #expect(afterCachedLoadOperations == ["getShow", "getShow"])
        #expect(cachedModel.refreshFailure != nil)
        guard case .success(let cachedResponse) = cachedModel.phase else {
            Issue.record("Expected cached detail response to survive failed revalidation")
            return
        }
        #expect(cachedResponse.data.id == 301)

        await cachedModel.reload(apiClient: client, favorites: ComedianFavoriteStore(), cache: cache)

        let afterReloadOperations = await recorder.operations
        #expect(afterReloadOperations == ["getShow", "getShow", "getShow"])
        #expect(cachedModel.refreshFailure == nil)
    }

    @Test("show detail favorite toggle dispatches through the favorite API boundary")
    func showDetailFavoriteToggleDispatchesFavoriteAPI() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "show-detail-favorite-toggle"
        )
        let recorder = FavoriteOperationRecorder()
        let client = makeClient(
            response: .success(DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail),
            favoriteRecorder: recorder
        )
        let favorites = ComedianFavoriteStore()
        let model = ShowDetailModel(showID: 301)
        await model.loadIfNeeded(apiClient: client, favorites: favorites)

        let initialOperations = await recorder.operations
        #expect(initialOperations == ["getShow"])
        #expect(favorites.value(for: "demo-comedian-101") == false)

        let result = await favorites.toggle(
            uuid: "demo-comedian-101",
            currentValue: favorites.value(for: "demo-comedian-101"),
            apiClient: client,
            authManager: authManager
        )

        guard case .updated(let nextValue) = result else {
            Issue.record("Expected favorite toggle to update, got \(result)")
            return
        }

        let finalOperations = await recorder.operations
        #expect(nextValue == true)
        #expect(favorites.value(for: "demo-comedian-101") == true)
        // The trailing getFavorites is the first-add saved-list refresh that
        // keeps the Favorites tab gate in sync.
        #expect(finalOperations == ["getShow", "addFavorite", "getFavorites"])
    }

    @Test("show detail navigation actions push the expected route payloads")
    func showDetailNavigationActionsPushRoutePayloads() throws {
        let response = DemoContent.showDetailResponse(id: 301) ?? DemoContent.primaryShowDetail
        let show = response.data
        let firstComedian = try #require(show.lineup?.first)
        let firstRelated = try #require(response.relatedShows.first)
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let targets: [EntityNavigationTarget] = [
            .club(show.club.id),
            .comedian(firstComedian.id),
            .show(firstRelated.id),
        ]
        let expectedRoutes: [AppRoute] = [
            .clubDetail(201),
            .comedianDetail(101),
            .showDetail(302),
        ]

        #expect(targets.map(\.route) == expectedRoutes)

        targets.forEach { coordinator.open($0) }

        #expect(coordinator.routes == expectedRoutes)
    }

    @Test("related shows use compact ticket rows")
    func relatedShowsUseCompactTicketRows() throws {
        let source = try String(contentsOf: showDetailViewSourceURL(), encoding: .utf8)

        #expect(source.contains("ShowRow(show: related, presentation: .compactTicket)"))
    }

    @Test("re-opening an entity already on the stack pops back to it instead of duplicating")
    func reopeningStackedEntityPopsBackInsteadOfDuplicating() {
        let coordinator = TypedNavigationCoordinator<AppRoute>()

        // club → show → comedian → the same club again: the cross-link cycle
        // that previously grew the stack one screen per tap, forever.
        coordinator.open(.club(201))
        coordinator.open(.show(301))
        coordinator.open(.comedian(101))
        coordinator.open(.club(201))

        #expect(coordinator.routes == [.clubDetail(201)])

        // A *different* club still pushes.
        coordinator.open(.club(202))
        #expect(coordinator.routes == [.clubDetail(201), .clubDetail(202)])

        // Re-opening the entity currently on top stays put.
        coordinator.open(.club(202))
        #expect(coordinator.routes == [.clubDetail(201), .clubDetail(202)])
    }

    @Test("show detail lineup derives explicit comedian role badges")
    func showLineupRendersExplicitRoleBadge() async throws {
        let headliner = Components.Schemas.ComedianLineup(
            name: "Jordan Temple",
            imageUrl: "",
            uuid: "comedian-role-1",
            id: 901,
            role: "Headliner"
        )
        let noRole = Components.Schemas.ComedianLineup(
            name: "No Role Comic",
            imageUrl: "",
            uuid: "comedian-role-2",
            id: 902
        )
        let blankRole = Components.Schemas.ComedianLineup(
            name: "Blank Role Comic",
            imageUrl: "",
            uuid: "comedian-role-3",
            id: 903,
            role: "   "
        )

        // HostedView accessibility-tree wiring is broken on iOS 26.x / 18.6, so
        // the rendered badge can't be asserted via requireText/findText
        // (TASK-2535). The tile shows ShowLineupPresentation.roleBadge(for:)
        // uppercased, so verify that pure derivation directly: an explicit role
        // surfaces, an absent or blank role does not, and an unrelated role
        // ("Feature") is never fabricated.
        #expect(ShowLineupPresentation.roleBadge(for: headliner) == "Headliner")
        #expect(ShowLineupPresentation.roleBadge(for: noRole) == nil)
        #expect(ShowLineupPresentation.roleBadge(for: blankRole) == nil)
    }

    @Test("show detail hero headshots start with inferred headliner and keep lineup images")
    func showHeroHeadshotsStartWithInferredHeadliner() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.lineup = [
            detailLineupComedian(
                name: "Feature Comic",
                imageUrl: "https://example.com/feature.jpg",
                uuid: "feature",
                id: 902,
                popularity: 0.42,
                showCount: 40
            ),
            detailLineupComedian(
                name: "Headliner Comic",
                imageUrl: "https://example.com/headliner.jpg",
                uuid: "headliner",
                id: 901,
                popularity: 0.98,
                showCount: 20
            ),
            detailLineupComedian(
                name: "No Image Comic",
                imageUrl: "   ",
                uuid: "no-image",
                id: 903,
                popularity: 0.99,
                showCount: 50
            )
        ]

        let headshots = ShowDetailPresentation.heroHeadshots(for: show)

        #expect(headshots.map(\.name) == ["Headliner Comic", "Feature Comic"])
        #expect(headshots.map(\.imageURL) == [
            "https://example.com/headliner.jpg",
            "https://example.com/feature.jpg"
        ])
        #expect(ShowDetailPresentation.heroThumbnailCaption(for: show) == "Headliner Comic")
    }

    @Test("show detail hero headshots are empty for open mics or image-less lineups")
    func showHeroHeadshotsEmptyForOpenMicOrNoImages() {
        var openMic = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        openMic.tags = [.init(slug: "open-mic", name: "Open Mic")]
        openMic.lineup = [
            detailLineupComedian(
                name: "Open Mic Comic",
                imageUrl: "https://example.com/open.jpg",
                uuid: "open",
                id: 904
            )
        ]

        var noImages = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        noImages.lineup = [
            detailLineupComedian(
                name: "Blank",
                imageUrl: " ",
                uuid: "blank",
                id: 905
            )
        ]

        #expect(ShowDetailPresentation.heroHeadshots(for: openMic).isEmpty)
        #expect(ShowDetailPresentation.heroHeadshots(for: noImages).isEmpty)
    }

    @Test("show detail hero omits countdown badges")
    func showHeroBadgeOmitsCountdown() {
        let show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        let badges = ShowDetailPresentation.heroBadges(for: show)

        #expect(badges.isEmpty)
    }

    @Test("show detail summary facts include event operations")
    func showSummaryFactsIncludeOperationalDetails() {
        let show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Distance", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "$30.00")
        #expect(facts.first { $0.label == "Venue" }?.value == "Comedy Cellar")
        #expect(facts.first { $0.label == "Distance" }?.value == "2.1 miles away")
    }

    @Test("show detail summary facts omit missing optional values and address")
    func showSummaryFactsOmitMissingValuesAndAddress() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = nil
        show.room = nil
        show.distanceMiles = nil
        show.address = "318 W. 53rd St, New York, NY"
        show.club.address = "318 W. 53rd St, New York, NY"

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "Price unavailable")
    }

    @Test("open-mic show detail substitutes RSVP for the price and reports isOpenMic")
    func showDetailOpenMicRendersRSVPVariant() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.name = "Late Set"
        show.tags = [.init(slug: "open-mic", name: "Open Mic")]

        #expect(ShowDetailPresentation.isOpenMic(show))
        let facts = ShowDetailPresentation.summaryFacts(for: show)
        #expect(facts.first { $0.label == "Tickets" }?.value == "RSVP")
    }

    @Test("non-open-mic show detail keeps the price value and reports !isOpenMic")
    func showDetailNonOpenMicRendersUnchanged() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.name = "Late Set"
        show.tags = [.init(slug: "weekly-showcase", name: "Weekly Showcase")]

        #expect(ShowDetailPresentation.isOpenMic(show) == false)
        let facts = ShowDetailPresentation.summaryFacts(for: show)
        #expect(facts.first { $0.label == "Tickets" }?.value != "RSVP")
    }

    @Test("show detail ticket cell targets ticket purchase URL")
    func showTicketCellTargetsTicketPurchaseURL() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = [
            .init(price: 30, purchaseUrl: "https://laughtrack.app/ticket-option", soldOut: false, _type: "General admission")
        ]
        show.cta = .init(url: "https://laughtrack.app/show-cta", label: "Buy tickets", isSoldOut: false)

        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://laughtrack.app/ticket-option")
    }

    @Test("show detail ticket click recorder sends the expected tracking payload")
    func showDetailTicketClickRecorderSendsExpectedTrackingPayload() async throws {
        let transport = StubClientTransport { request, body, _, operationID in
            #expect(operationID == "recordTicketClick")
            #expect(request.method == .post)
            #expect(request.path == "/ticket-clicks")
            let bytes = try await Data(collecting: body ?? HTTPBody(), upTo: 4096)
            let payload = try JSONSerialization.jsonObject(with: bytes) as? [String: Any]
            #expect(payload?["showId"] as? Int == 301)
            #expect(payload?["clubId"] as? Int == 201)
            #expect(payload?["destinationUrl"] as? String == "https://laughtrack.app/ticket-option")
            #expect(payload?["sourceSurface"] as? String == "ios_show_detail")
            return (HTTPResponse(status: .created), nil)
        }
        let client = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: transport
        )
        let recorder = ShowDetailTicketClickRecorder(apiClient: client)

        let didRecord = await recorder.record(
            showID: 301,
            clubID: 201,
            destinationURL: URL(string: "https://laughtrack.app/ticket-option")!
        )

        #expect(didRecord == true)
        #expect(transport.capturedRequests.map { $0.operationID } == ["recordTicketClick"])
    }

    @Test("show detail calendar event uses show venue and ticket URL")
    func showCalendarEventUsesShowVenueAndTicketURL() {
        var show = DemoContent.showDetailResponse(id: 301)?.data ?? DemoContent.primaryShowDetail.data
        show.tickets = [
            .init(price: 30, purchaseUrl: "https://laughtrack.app/ticket-option", soldOut: false, _type: "General admission")
        ]

        let event = ShowCalendarEventPresentation.event(for: show)

        #expect(event.title == show.name)
        #expect(event.startDate == show.date)
        #expect(event.endDate == show.date.addingTimeInterval(2 * 60 * 60))
        #expect(event.location?.contains(show.club.name) == true)
        #expect(event.url?.absoluteString == "https://laughtrack.app/ticket-option")
    }

    private func makeClient(
        response: MockShowDetailTransport.Response,
        favoriteRecorder: FavoriteOperationRecorder? = nil
    ) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: MockShowDetailTransport(response: response, favoriteRecorder: favoriteRecorder)
        )
    }

    private func showDetailViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Detail/Views/ShowDetailView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

}

private actor FavoriteOperationRecorder {
    private(set) var operations: [String] = []

    func record(_ operation: String) {
        operations.append(operation)
    }
}

private func detailLineupComedian(
    name: String,
    imageUrl: String,
    uuid: String,
    id: Int,
    popularity: Double = 0,
    showCount: Int = 0
) -> Components.Schemas.ComedianLineup {
    Components.Schemas.ComedianLineup(
        name: name,
        imageUrl: imageUrl,
        uuid: uuid,
        id: id,
        socialData: .init(id: id, popularity: popularity),
        showCount: showCount
    )
}

private struct MockShowDetailTransport: ClientTransport {
    enum Response {
        case success(Components.Schemas.ShowDetailResponse)
        case status(HTTPResponse.Status)
    }

    let response: Response
    let favoriteRecorder: FavoriteOperationRecorder?

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        await favoriteRecorder?.record(operationID)

        if operationID == "addFavorite" || operationID == "removeFavorite" {
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(
                    status: .ok,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(
                    try encoder.encode(
                        Components.Schemas.FavoriteResponse(
                            data: .init(isFavorited: operationID == "addFavorite")
                        )
                    )
                )
            )
        }

        // A first add-toggle force-refreshes the saved-favorites list so
        // surfaces gated on it (the Favorites tab) update immediately.
        if operationID == "getFavorites" {
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(Components.Schemas.FavoriteListResponse(data: [])))
            )
        }

        #expect(operationID == "getShow")
        #expect(request.method == .get)

        switch response {
        case .success(let payload):
            let encoder = APIMockEncoder.make()

            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(payload))
            )
        case .status(let status):
            // ErrorResponse schema requires `error` — empty `{}` makes the OpenAPI
            // decoder throw and the model falls into the network catch.
            return (
                HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"mock"}"#)
            )
        }
    }
}

@Suite("Show ticket availability")
@MainActor
struct ShowTicketAvailabilityTests {
    private func show() -> Components.Schemas.ShowDetail {
        var show = DemoContent.primaryShowDetail.data
        show.name = "Evening Comedy"
        show.tags = nil
        show.soldOut = false
        show.tickets = [.init(price: 30, purchaseUrl: "https://tickets.example.com/show", soldOut: false, _type: "General admission")]
        show.cta = .init(url: nil, label: "Buy tickets", isSoldOut: false)
        show.showPageUrl = ""
        return show
    }

    @Test("available tickets retain their price and purchase action")
    func availableTickets() {
        let show = show()
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "$30.00")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://tickets.example.com/show")
    }

    @Test("explicit show or complete inventory sellout disables purchases", arguments: [true, false])
    func explicitSellout(showLevel: Bool) {
        var show = show()
        show.soldOut = showLevel
        show.tickets?[0].soldOut = !showLevel
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Sold out")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }

    @Test("sold out CTA with a destination remains an explicit inventory signal")
    func soldOutCTA() {
        var show = show()
        show.cta = .init(url: "https://tickets.example.com/show", label: "Buy tickets", isSoldOut: true)
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Sold out")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }

    @Test("missing links including legacy CTA flags do not claim sold out", arguments: [true, false])
    func missingLinks(legacyFlag: Bool) {
        var show = show()
        show.tickets = nil
        show.soldOut = nil
        show.cta.isSoldOut = legacyFlag
        let summary = ShowPricePresentation.detailTicketSummary(for: show)
        #expect(summary == "Ticket link unavailable")
        #expect(ShowPricePresentation.detailTicketExplanation(summary) != nil)
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }

    @Test("unknown price keeps an available purchase action")
    func unknownPrice() {
        var show = show()
        show.tickets?[0].price = nil
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Price unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) != nil)
        #expect(ShowPricePresentation.detailTicketExplanation("Price unavailable") == ShowPricePresentation.priceUnavailableExplanation)
    }

    @Test("invalid destinations are unavailable without a valid fallback", arguments: ["", "garbage", "not a url", "javascript:alert(1)", "mailto:tickets@example.com", "https://", "https://example.com/bad path"])
    func malformedLinks(rawURL: String) {
        var show = show()
        show.tickets?[0].purchaseUrl = rawURL
        show.cta.url = rawURL
        show.showPageUrl = rawURL
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Ticket link unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }

    @Test("invalid ticket URLs fall back to the CTA then the show page")
    func validFallbacks() {
        var show = show()
        show.tickets?[0].purchaseUrl = "javascript:alert(1)"
        show.cta.url = "https://tickets.example.com/cta"
        show.showPageUrl = "https://venue.example.com/event"
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == show.cta.url)
        show.cta.url = nil
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == show.showPageUrl)
    }

    @Test("supported relative and schemeless destinations remain usable", arguments: ["tickets.example.com/show", "/show/301"])
    func normalizedDestinations(rawURL: String) {
        var show = show()
        show.tickets?[0].purchaseUrl = rawURL
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == URL.normalizedExternalURL(rawURL))
    }

    @Test("open mic RSVP does not conceal unavailable or sold out states")
    func openMicStates() {
        var show = show()
        show.name = "Open Mic"
        #expect(ShowDetailPresentation.summaryFacts(for: show).last?.value == "RSVP")
        show.tickets = nil
        #expect(ShowDetailPresentation.summaryFacts(for: show).last?.value == "Ticket link unavailable")
        show.soldOut = true
        #expect(ShowDetailPresentation.summaryFacts(for: show).last?.value == "Sold out")
    }
}

@Suite("Show available tier prices")
@MainActor
struct ShowAvailableTierPriceTests {
    private func show() -> Components.Schemas.ShowDetail {
        var show = DemoContent.primaryShowDetail.data
        show.name = "Evening Comedy"
        show.tags = nil
        show.soldOut = false
        show.cta = .init(url: nil, label: "Buy tickets", isSoldOut: false)
        show.showPageUrl = ""
        show.tickets = [
            .init(price: 10, purchaseUrl: "https://tickets.example.com/early", soldOut: true, _type: "Early bird"),
            .init(price: 30, purchaseUrl: "https://tickets.example.com/general", soldOut: false, _type: "General admission")
        ]
        return show
    }

    @Test("sold-out cheap tiers do not understate the available price", arguments: [0.0, 10.0])
    func soldOutCheaperTier(price: Double) {
        var show = show()
        show.tickets?[0].price = price
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "$30.00")
        #expect(ShowDetailPresentation.summaryFacts(for: show).last?.value == "$30.00")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://tickets.example.com/general")
    }

    @Test("the lowest of multiple available tiers determines the detail price")
    func multipleAvailableTiers() {
        var show = show()
        show.tickets?.append(.init(price: 20, purchaseUrl: "https://tickets.example.com/balcony", soldOut: false, _type: "Balcony"))
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "$20.00")
    }

    @Test("tiers without an explicit sellout flag remain eligible")
    func unknownSelloutFlag() {
        var show = show()
        show.tickets?[1].soldOut = nil
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "$30.00")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://tickets.example.com/general")
    }

    @Test("available free tiers still display Free")
    func availableFreeTier() {
        var show = show()
        show.tickets?[1].price = 0
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Free")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) != nil)
    }

    @Test("unknown available prices do not borrow a sold-out tier price")
    func unknownAvailablePrice() {
        var show = show()
        show.tickets?[1].price = nil
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Price unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://tickets.example.com/general")
    }

    @Test("empty inventory preserves a usable fallback without inventing a price", arguments: [true, false])
    func emptyInventory(hasFallback: Bool) {
        var show = show()
        show.tickets = []
        show.showPageUrl = hasFallback ? "https://venue.example.com/event" : ""
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == (hasFallback ? "Price unavailable" : "Ticket link unavailable"))
        #expect((ShowDetailPresentation.primaryTicketURL(for: show) != nil) == hasFallback)
    }

    @Test("available inventory without any destination reports an unavailable link")
    func missingLinks() {
        var show = show()
        show.tickets?[1].purchaseUrl = ""
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Ticket link unavailable")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }

    @Test("all sold-out inventory retains the sold-out label and no purchase action")
    func allSoldOut() {
        var show = show()
        show.tickets?[1].soldOut = true
        #expect(ShowPricePresentation.detailTicketSummary(for: show) == "Sold out")
        #expect(ShowDetailPresentation.primaryTicketURL(for: show) == nil)
    }
}


@Suite("Past show presentation", .serialized)
@MainActor
struct ShowPastEventPresentationTests {
    // An absolute instant near midnight makes these cases independent of the
    // device calendar, time zone, and the day on which this suite runs.
    private let now = Date(timeIntervalSince1970: 1_789_689_600)

    @Test("future shows retain upcoming actions even across a date boundary", arguments: [0.001, 1.0, 86_400.0])
    func futureState(offset: TimeInterval) {
        let presentation = ShowPastEventPresentation(showDate: now.addingTimeInterval(offset), now: now)
        #expect(presentation.isUpcoming)
        #expect(presentation.statusMessage == nil)
        #expect(ShowSavedActionPresentation.shouldShow(isSaved: false, showDate: now.addingTimeInterval(offset), now: now))
    }

    @Test("the exact start instant and earlier dates are historical", arguments: [0.0, -0.001, -1.0, -86_400.0])
    func startedState(offset: TimeInterval) {
        let presentation = ShowPastEventPresentation(showDate: now.addingTimeInterval(offset), now: now)
        #expect(!presentation.isUpcoming)
        #expect(presentation.statusMessage != nil)
        #expect(!ShowSavedActionPresentation.shouldShow(isSaved: false, showDate: now.addingTimeInterval(offset), now: now))
    }

    @Test("a just-started show never claims its unknown end time has passed")
    func justStartedCopyDoesNotInventEndTime() throws {
        let presentation = ShowPastEventPresentation(showDate: now.addingTimeInterval(-1), now: now)
        let message = try #require(presentation.statusMessage).lowercased()
        #expect(!message.contains("ended"))
        #expect(!message.contains("finished"))
        #expect(message.contains("start"))
    }

    @Test("existing saved shows remain removable at and after their start", arguments: [0.0, -1.0, -86_400.0])
    func savedPastShowRemainsRemovable(offset: TimeInterval) {
        #expect(ShowSavedActionPresentation.shouldShow(isSaved: true, showDate: now.addingTimeInterval(offset), now: now))
    }

    @Test("historical regular shows and open mics remove ticket facts and destinations", arguments: [false, true], [0.0, -1.0, -86_400.0])
    func historicalSummaryDecisions(isOpenMic: Bool, offset: TimeInterval) {
        var show = fixture()
        show.name = isOpenMic ? "Open Mic" : "Evening Comedy"
        show.tags = nil
        show.date = now.addingTimeInterval(offset)
        let presentation = ShowPastEventPresentation(showDate: show.date, now: now)
        #expect(ShowDetailPresentation.isOpenMic(show) == isOpenMic)
        #expect(presentation.ticketURL(for: show) == nil)
        #expect(!presentation.summaryFacts(for: show).contains { $0.label == "Tickets" })
        #expect(presentation.summaryFacts(for: show).contains { $0.label == "When" })
        #expect(presentation.summaryFacts(for: show).contains { $0.label == "Venue" })
        #expect(presentation.venueActionLabel == "Find upcoming shows")
    }

    @Test("future summaries preserve ticket facts and the usable destination", arguments: [false, true])
    func futureSummaryDecisions(isOpenMic: Bool) {
        var show = fixture()
        show.name = isOpenMic ? "Open Mic" : "Evening Comedy"
        show.tags = nil
        show.date = now.addingTimeInterval(1)
        let presentation = ShowPastEventPresentation(showDate: show.date, now: now)
        #expect(presentation.ticketURL(for: show)?.absoluteString == "https://tickets.example.com/show")
        #expect(presentation.summaryFacts(for: show).first { $0.label == "Tickets" }?.value == (isOpenMic ? "RSVP" : "$25.00"))
        #expect(presentation.venueActionLabel == "Open venue")
    }

    #if canImport(UIKit)
    @Test("capture historical and future summaries for manual visual review", arguments: ["past", "future", "past-open-mic"])
    func captureSummaryForReview(scenario: String) async throws {
        var show = fixture()
        let isOpenMic = scenario == "past-open-mic"
        show.name = isOpenMic ? "Open Mic" : "Evening Comedy"
        show.tags = nil
        show.date = now.addingTimeInterval(scenario == "future" ? 60 : -1)
        let presentation = ShowPastEventPresentation(showDate: show.date, now: now)
        // This simulator does not expose SwiftUI accessibility nodes for the
        // ticket card. These captures support manual review; behavior is tested
        // above through the same presentation decisions used by the view.
        let host = HostedView(
            VStack(alignment: .leading, spacing: 16) {
                if let message = presentation.statusMessage {
                    Text(message)
                }
                ShowSummarySection(
                    show: show,
                    isOpenMic: isOpenMic,
                    now: now,
                    openClub: {},
                    openTicketURL: { _ in },
                    addToCalendar: {}
                )
            }
            .padding(16)
        )
        await host.settle()
        let data = try #require(try host.snapshot().pngData())
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("task4018-\(scenario).png")
        try data.write(to: path)
        print("Past show review capture: \(path.path)")
    }
    #endif

    private func fixture() -> Components.Schemas.ShowDetail {
        var show = DemoContent.primaryShowDetail.data
        show.soldOut = false
        show.tickets = [.init(price: 25, purchaseUrl: "https://tickets.example.com/show", soldOut: false)]
        show.cta = .init(url: "https://tickets.example.com/show", label: "Buy tickets", isSoldOut: false)
        return show
    }
}


@Suite("Show ticket navigation", .timeLimit(.minutes(1)))
@MainActor
struct ShowTicketNavigationTests {
    private let destination = URL(string: "https://tickets.example.com/show/301?tier=general")!

    @Test("a suspended tracking request never delays navigation")
    func suspendedTrackingDoesNotDelayNavigation() async {
        let transport = SuspendedTicketNavigationTransport()
        let recorder = makeRecorder(transport: transport)
        var openedURLs: [URL] = []

        let tracking = recorder.open(showID: 301, clubID: 201, destinationURL: destination) {
            openedURLs.append($0)
        }

        // No actor yield: navigation must happen in the original tap handling turn.
        #expect(openedURLs == [destination])
        for await _ in transport.started { break }
        #expect(openedURLs == [destination])
        await transport.release()
        await tracking.value
        #expect(openedURLs == [destination])
    }

    @Test("tracking network errors and cancellation cannot suppress navigation", arguments: [false, true])
    func failedTrackingDoesNotPreventNavigation(cancelled: Bool) async {
        let transport = StubClientTransport { _, _, _, _ in
            if cancelled { throw CancellationError() }
            throw URLError(.notConnectedToInternet)
        }
        var openedURLs: [URL] = []
        let tracking = makeRecorder(transport: transport).open(
            showID: 301, clubID: 201, destinationURL: destination
        ) { openedURLs.append($0) }

        #expect(openedURLs == [destination])
        await tracking.value
        #expect(openedURLs == [destination])
        #expect(transport.capturedRequests.count == 1)
    }

    @Test("cancelling in-flight tracking preserves the already opened destination")
    func cancellingTrackingDoesNotUndoNavigation() async {
        let transport = SuspendedTicketNavigationTransport()
        var openedURLs: [URL] = []
        let tracking = makeRecorder(transport: transport).open(
            showID: 301, clubID: 201, destinationURL: destination
        ) { openedURLs.append($0) }

        #expect(openedURLs == [destination])
        for await _ in transport.started { break }
        tracking.cancel()
        await transport.release()
        await tracking.value
        #expect(openedURLs == [destination])
    }

    @Test("one ticket tap records exactly one event with its show, club and destination")
    func normalTapRecordsOneCorrectEvent() async {
        let transport = StubClientTransport { request, body, _, operationID in
            #expect(operationID == "recordTicketClick")
            #expect(request.method == .post)
            #expect(request.path == "/ticket-clicks")
            let bytes = try await Data(collecting: body ?? HTTPBody(), upTo: 4096)
            let payload = try JSONSerialization.jsonObject(with: bytes) as? [String: Any]
            #expect(payload?["showId"] as? Int == 301)
            #expect(payload?["clubId"] as? Int == 201)
            #expect(payload?["destinationUrl"] as? String == "https://tickets.example.com/show/301?tier=general")
            #expect(payload?["sourceSurface"] as? String == "ios_show_detail")
            return (HTTPResponse(status: .created), nil)
        }
        var openedURLs: [URL] = []
        let tracking = makeRecorder(transport: transport).open(
            showID: 301, clubID: 201, destinationURL: destination
        ) { openedURLs.append($0) }

        #expect(openedURLs == [destination])
        await tracking.value
        #expect(openedURLs == [destination])
        #expect(transport.capturedRequests.map { $0.operationID } == ["recordTicketClick"])
    }

    @Test("a ticket tap presents in-app Safari immediately and only once")
    func ticketTapPresentsSafariOnce() async {
        let transport = SuspendedTicketNavigationTransport()
        var safariURL: URL?
        var safariAssignments: [URL?] = []
        var systemURLs: [URL] = []
        let presentedURL = Binding<URL?>(
            get: { safariURL },
            set: { safariURL = $0; safariAssignments.append($0) }
        )
        let openURL = OpenURLAction { url in
            systemURLs.append(url)
            return .handled
        }
        let tracking = makeRecorder(transport: transport).open(
            showID: 301, clubID: 201, destinationURL: destination
        ) { url in
            ExternalLinkRouter.route(url, presentedURL: presentedURL, openURL: openURL)
        }

        #expect(safariURL == destination)
        #expect(safariAssignments == [destination])
        #expect(systemURLs.isEmpty)
        for await _ in transport.started { break }
        await transport.release()
        await tracking.value
        #expect(safariAssignments == [destination])
        #expect(systemURLs.isEmpty)
    }

    private func makeRecorder(transport: any ClientTransport) -> ShowDetailTicketClickRecorder {
        ShowDetailTicketClickRecorder(apiClient: Client(
            serverURL: URL(string: "https://example.com")!, transport: transport
        ))
    }
}

private actor SuspendedTicketNavigationTransport: ClientTransport {
    nonisolated let started: AsyncStream<Void>
    private let startedContinuation: AsyncStream<Void>.Continuation
    private var responseContinuation: CheckedContinuation<Void, Never>?

    init() {
        let stream = AsyncStream<Void>.makeStream()
        started = stream.stream
        startedContinuation = stream.continuation
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        #expect(operationID == "recordTicketClick")
        await withCheckedContinuation { continuation in
            responseContinuation = continuation
            startedContinuation.yield(())
            startedContinuation.finish()
        }
        try Task.checkCancellation()
        return (HTTPResponse(status: .created), nil)
    }

    func release() {
        responseContinuation?.resume()
        responseContinuation = nil
    }
}
