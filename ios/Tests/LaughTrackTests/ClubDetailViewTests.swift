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
    @Test("club detail loads venue data without the redundant related-content search")
    func clubDetailLoadsVenueWithoutRelatedContentSearch() async throws {
        let model = ClubDetailModel(clubId: 201)
        let transport = MockClubDetailTransport(
            clubResponse: .success(.init(data: primaryClub)),
            highlightsResponse: .success(.init(data: highlights()))
        )
        await model.loadIfNeeded(apiClient: makeClient(transport: transport))

        guard case .success(let content) = model.phase else {
            Issue.record("Expected success phase, got \(model.phase)")
            return
        }

        #expect(content.club.name == "Comedy Cellar")
        #expect(transport.operationIDs == ["getClub"])
    }

    @Test("club detail places venue actions in the hero")
    func clubDetailPlacesVenueActionsInHero() {
        let actions = ClubDetailHeroPresentation.actions(for: primaryClub)

        #expect(actions.map(\.title) == ["Website", "Directions"])
        #expect(actions.map(\.systemImage) == ["arrow.up.right", "map.fill"])
        #expect(actions.allSatisfy { $0.url != nil })
    }

    @Test("club detail uses the dedicated hero image when present")
    func clubDetailUsesDedicatedHeroImageWhenPresent() {
        #expect(ClubDetailHeroPresentation.imageURL(for: primaryClub) == "https://example.com/club-hero.png")
    }

    @Test("club detail falls back to the listing imageUrl when no hero image is present")
    func clubDetailFallsBackToImageUrlWhenNoHeroImageIsPresent() {
        let club = Components.Schemas.ClubDetail(
            id: 202,
            name: "No Hero Club",
            imageUrl: "https://example.com/logo.png",
            heroImageUrl: "",
            website: "https://example.com",
            address: "100 Main St"
        )

        #expect(ClubDetailHeroPresentation.imageURL(for: club) == "https://example.com/logo.png")
    }

    @Test("club detail returns nil when both hero and listing images are empty")
    func clubDetailReturnsNilWhenBothImagesAreEmpty() {
        let club = Components.Schemas.ClubDetail(
            id: 203,
            name: "No Artwork Club",
            imageUrl: "",
            heroImageUrl: "",
            website: "https://example.com",
            address: "100 Main St"
        )

        #expect(ClubDetailHeroPresentation.imageURL(for: club) == nil)
    }

    @Test("club detail uses stack-aware Back and Home navigation chrome")
    func clubDetailUsesStackAwareNavigationChrome() throws {
        let source = try String(
            contentsOf: detailSourceURL(named: "ClubDetailView.swift"),
            encoding: .utf8
        )

        #expect(source.contains("DetailChromeBar("))
        #expect(source.contains("onBack: { coordinator.pop() }"))
        #expect(source.contains("onHome: coordinator.detailHomeAction"))
    }

    @Test("club detail replaces visible venue artwork with the tonight marquee")
    func clubDetailUsesTonightAsPrimaryMarqueeContent() throws {
        let source = try String(
            contentsOf: detailSourceURL(named: "ClubDetailView.swift"),
            encoding: .utf8
        )
        let titlePosition = try #require(source.range(of: "title: club.name"))
        let actionPosition = try #require(source.range(of: "actionPlacement: .belowTitle"))
        let boardPosition = try #require(source.range(of: "ClubDetailTonightMarqueeSection("))

        #expect(titlePosition.lowerBound < actionPosition.lowerBound)
        #expect(actionPosition.lowerBound < boardPosition.lowerBound)
        #expect(source.contains("VStack(spacing: ClubVenueMarqueeStyle.artworkToBoardSpacing)"))
        #expect(source.contains("imageURL: ClubDetailHeroPresentation.imageURL(for: club) ?? \"\""))
        #expect(source.contains("thumbnailStyle: .clubMarquee"))
        #expect(source.contains("showsThumbnail: false"))
        #expect(source.contains("Set to true to restore venue artwork above the Tonight marquee."))
        #expect(source.contains("fallbackSystemImage: ArtworkFallbackKind.club.systemImage"))
        #expect(source.contains("actionStyle: .compactPill"))
        #expect(source.contains("bottomPadding: 0"))
        #expect(source.contains("Text(\"Tonight\")"))
        #expect(source.contains("summary: eveningSummary"))
        #expect(source.contains("Text(viewAllLabel)"))
        #expect(!source.contains("coordinator.open(.show(show.id))"))
        #expect(source.contains("proxy.scrollTo("))
    }

    @Test("club detail surfaces API failures explicitly")
    func clubDetailShowsErrorState() async throws {
        let model = ClubDetailModel(clubId: 201)
        await model.loadIfNeeded(
            apiClient: makeClient(
                clubResponse: .status(.notFound),
                highlightsResponse: .success(.init(data: highlights()))
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

    @Test("club evening summary deduplicates parent identities and ranks unique performers")
    func clubEveningSummaryDeduplicatesAndRanksPerformers() throws {
        let calendar = Calendar(identifier: .gregorian)
        let base = try #require(calendar.date(from: DateComponents(
            timeZone: TimeZone(secondsFromGMT: 0),
            year: 2026,
            month: 7,
            day: 30,
            hour: 18
        )))
        let headliner = lineup(id: 101, name: "Headliner", popularity: 95, showCount: 10)
        let headlinerAlias = lineup(
            id: 901,
            name: "Headliner Alias",
            popularity: 1,
            showCount: 1,
            parentComedian: headliner
        )
        let shows = [
            show(
                id: 301,
                name: "Late",
                date: base.addingTimeInterval(2 * 60 * 60),
                lineup: [headlinerAlias, lineup(id: 104, name: "Fourth", popularity: 70)]
            ),
            show(
                id: 302,
                name: "Early",
                date: base,
                lineup: [headliner, lineup(id: 102, name: "Second by ID", popularity: 80, showCount: 20)]
            ),
            show(
                id: 303,
                name: "Middle",
                date: base.addingTimeInterval(60 * 60),
                lineup: [lineup(id: 103, name: "Third by ID", popularity: 80, showCount: 20)]
            ),
            show(
                id: 304,
                name: "Same time",
                date: base.addingTimeInterval(60 * 60),
                lineup: [lineup(id: 104, name: "Fourth", popularity: 70)]
            ),
        ]

        let summary = try #require(ClubDetailHighlightsPresentation.eveningSummary(
            from: highlights(tonightShows: shows)
        ))

        #expect(summary.performerNames == ["Headliner", "Second by ID", "Third by ID"])
        #expect(summary.remainingPerformerCount == 1)
        #expect(summary.showCount == 4)
        #expect(summary.localizedStartTimes == [shows[1], shows[2], shows[0]].map {
            ShowFormatting.dateStack($0.date, timezoneID: $0.timezone).time
        })
    }

    @Test("club evening summary handles one performer and missing-lineup fallback")
    func clubEveningSummaryHandlesSparseLineups() throws {
        let date = Date(timeIntervalSince1970: 1_800_000_000)
        let single = try #require(ClubDetailHighlightsPresentation.eveningSummary(
            from: highlights(tonightShows: [
                show(id: 301, name: "Solo show", date: date, lineup: [
                    lineup(id: 101, name: "Solo", popularity: nil),
                ]),
            ])
        ))
        #expect(single.performerNames == ["Solo"])
        #expect(single.remainingPerformerCount == 0)
        #expect(single.showCount == 1)

        let earliest = show(id: 302, name: "Earliest fallback", date: date, lineup: nil)
        let later = show(
            id: 303,
            name: "Later fallback",
            date: date.addingTimeInterval(60 * 60),
            lineup: []
        )
        let noLineup = try #require(ClubDetailHighlightsPresentation.eveningSummary(
            from: highlights(tonightShows: [
                later,
                earliest,
            ])
        ))
        #expect(noLineup.performerNames == [ShowTitlePresentation.title(for: earliest)])
        #expect(noLineup.remainingPerformerCount == 0)
        #expect(noLineup.showCount == 2)
    }

    @Test("club evening summary stays absent without tonight shows")
    func clubEveningSummaryPreservesNoTonightFallback() {
        #expect(ClubDetailHighlightsPresentation.eveningSummary(
            from: highlights(tonightShows: [], nextShow: relatedShows[1])
        ) == nil)
        #expect(ClubDetailHighlightsPresentation.eveningSummary(
            from: highlights(tonightShows: [], nextShow: nil)
        ) == nil)
    }

    @Test("club pinned shows can be switched to Today without clearing club scope")
    func clubPinnedShowsTodayFilter() throws {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = try #require(TimeZone(secondsFromGMT: 0))
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let filter = PinnedShowsListPresentation.todayFilter(now: now, calendar: calendar)

        #expect(filter.isActive)
        #expect(filter.from == calendar.startOfDay(for: now))
        #expect(filter.to == filter.from)

        let clubSource = try String(
            contentsOf: detailSourceURL(named: "ClubDetailView.swift"),
            encoding: .utf8
        )
        let pinnedSource = try String(
            contentsOf: appSourceURL(relativePath: "Components/PinnedShowsList.swift"),
            encoding: .utf8
        )
        #expect(clubSource.contains("ScrollViewReader { proxy in"))
        #expect(clubSource.contains("proxy.scrollTo("))
        #expect(clubSource.contains("todayRequest: pinnedShowsTodayRequest"))
        #expect(pinnedSource.contains("pinnedClubName: pinnedClubName"))
        #expect(pinnedSource.contains("ShowsListView(apiClient: apiClient, model: model, compactMode: true)"))
        #expect(pinnedSource.contains(".onChange(of: todayRequest)"))
    }

    @Test("club highlights expose only API-qualified frequent performers")
    func clubHighlightFrequentPerformers() {
        #expect(highlights().frequentPerformers.map(\.name) == ["Mark Normand", "Atsuko Okatsuka", "Sam Jay"])
        #expect(highlights(frequentPerformers: []).frequentPerformers.isEmpty)
    }

    @Test("club highlight failure leaves venue content successful and performs no show search")
    func clubHighlightFailureIsIndependent() async {
        let clubModel = ClubDetailModel(clubId: 201)
        let highlightsModel = ClubHighlightsModel(clubId: 201)
        let transport = MockClubDetailTransport(
            clubResponse: .success(.init(data: primaryClub)),
            highlightsResponse: .status(.internalServerError)
        )
        let client = makeClient(transport: transport)

        await clubModel.loadIfNeeded(apiClient: client)
        await highlightsModel.loadIfNeeded(apiClient: client)

        guard case .success(let content) = clubModel.phase else {
            Issue.record("Expected club success, got \(clubModel.phase)")
            return
        }
        #expect(content.club.name == "Comedy Cellar")
        guard case .failure = highlightsModel.phase else {
            Issue.record("Expected independent highlight failure, got \(highlightsModel.phase)")
            return
        }
        #expect(transport.operationIDs == ["getClub", "getClubHighlights"])
    }

    @Test("club highlight actions preserve entity navigation and stable accessibility IDs")
    func clubHighlightActionsAndIdentifiers() throws {
        #expect(EntityNavigationTarget.show(301).route == .showDetail(301))
        #expect(EntityNavigationTarget.comedian(101).route == .comedianDetail(101))
        #expect(LaughTrackViewTestID.clubDetailHighlightSection == "laughtrack.club-detail.highlight-section")
        #expect(LaughTrackViewTestID.clubDetailHighlightShowButton(301) == "laughtrack.club-detail.highlight-show-301")
        #expect(LaughTrackViewTestID.clubDetailFrequentPerformersSection == "laughtrack.club-detail.frequent-performers-section")
        #expect(LaughTrackViewTestID.clubDetailPerformerButton(101) == "laughtrack.club-detail.performer-101")

        let source = try String(
            contentsOf: detailSourceURL(named: "ClubDetailView.swift"),
            encoding: .utf8
        )
        #expect(!source.contains("clubDetailHighlightShowButton(row.show.id)"))
        #expect(source.contains("if eveningSummary == nil, let nextShow = highlights.nextShow"))
        #expect(source.contains("featuredShow: .init(title: \"Next up\", show: nextShow)"))
        #expect(source.contains("coordinator.open(.show(nextShow.id))"))
        #expect(source.contains("coordinator.open(.comedian(performer.id))"))
        #expect(source.contains("LaughTrackViewTestID.clubDetailHighlightSection"))
        #expect(source.contains("LaughTrackViewTestID.clubDetailFrequentPerformersSection"))
        #expect(source.contains("Text(\"Tonight\")"))
        #expect(!source.contains("Text(\"Tonight's\")"))
        #expect(source.contains("ClubVenueMarqueeStyle.paper"))
        #expect(source.contains("ClubVenueMarqueeStyle.bulbStroke"))
        #expect(source.contains("Text(viewAllLabel)"))
        #expect(source.contains("pinnedShowsTodayRequest += 1"))
        #expect(source.contains("return \"View all \\(summary.showCount) \\(noun)\""))
    }

    @Test("frequent performers render after pinned shows")
    func frequentPerformersFollowPinnedShows() throws {
        let source = try String(
            contentsOf: detailSourceURL(named: "ClubDetailView.swift"),
            encoding: .utf8
        )
        let pinnedShowsPosition = try #require(source.range(of: "PinnedShowsList("))
        let frequentPerformersPosition = try #require(
            source.range(of: "ClubDetailFrequentPerformersSection(")
        )

        #expect(pinnedShowsPosition.lowerBound < frequentPerformersPosition.lowerBound)
    }

    private func makeClient(
        clubResponse: MockClubDetailTransport.EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>,
        highlightsResponse: MockClubDetailTransport.EntityResponse<Components.Schemas.ClubHighlightsResponse>
    ) -> Client {
        makeClient(
            transport: MockClubDetailTransport(
                clubResponse: clubResponse,
                highlightsResponse: highlightsResponse
            )
        )
    }

    private func makeClient(transport: MockClubDetailTransport) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
    }

    private var primaryClub: Components.Schemas.ClubDetail {
        .init(
            id: 201,
            name: "Comedy Cellar",
            imageUrl: "https://example.com/club.png",
            heroImageUrl: "https://example.com/club-hero.png",
            website: "https://www.comedycellar.com",
            address: "117 MacDougal St, New York, NY",
            zipCode: "10012",
            phoneNumber: "(212) 254-3480"
        )
    }

    private var relatedShows: [Components.Schemas.Show] {
        [
            show(id: 301, name: "Mark Normand and Friends"),
            show(id: 302, name: "Late show"),
        ]
    }

    private func show(
        id: Int,
        name: String,
        date: Date = Date().addingTimeInterval(60 * 60 * 24),
        lineup: [Components.Schemas.ComedianLineup]? = nil,
        timezone: String? = nil
    ) -> Components.Schemas.Show {
        .init(
            id: id,
            clubId: 201,
            clubName: "Comedy Cellar",
            date: date,
            tickets: nil,
            name: name,
            socialData: nil,
            lineup: lineup,
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: 2.0,
            timezone: timezone
        )
    }

    private func lineup(
        id: Int,
        name: String,
        popularity: Double?,
        showCount: Int = 12,
        parentComedian: Components.Schemas.ComedianLineup? = nil
    ) -> Components.Schemas.ComedianLineup {
        .init(
            name: name,
            imageUrl: "https://example.com/comedian-\(id).png",
            uuid: "demo-lineup-\(id)",
            id: id,
            socialData: .init(id: id, popularity: popularity),
            showCount: showCount,
            parentComedian: parentComedian
        )
    }

    private func highlights(
        tonightShows: [Components.Schemas.Show]? = nil,
        nextShow: Components.Schemas.Show? = nil,
        frequentPerformers: [Components.Schemas.ComedianListItem]? = nil
    ) -> Components.Schemas.ClubHighlights {
        .init(
            tonightShows: tonightShows ?? [relatedShows[0]],
            nextShow: nextShow,
            frequentPerformers: frequentPerformers ?? [
                performer(id: 101, name: "Mark Normand"),
                performer(id: 102, name: "Atsuko Okatsuka"),
                performer(id: 103, name: "Sam Jay"),
            ]
        )
    }

    private func performer(id: Int, name: String) -> Components.Schemas.ComedianListItem {
        .init(
            id: id,
            uuid: "demo-comedian-\(id)",
            name: name,
            imageUrl: "https://example.com/\(id).png",
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
            showCount: 12
        )
    }

    private func detailSourceURL(named fileName: String, filePath: String = #filePath) -> URL {
        appSourceURL(
            relativePath: "Detail/Views/\(fileName)",
            filePath: filePath
        )
    }

    private func appSourceURL(
        relativePath: String,
        filePath: String = #filePath
    ) -> URL {
        URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Sources/LaughTrackApp/\(relativePath)")
    }
}

private final class MockClubDetailTransport: ClientTransport, @unchecked Sendable {
    enum EntityResponse<Payload> {
        case success(Payload)
        case status(HTTPResponse.Status)
    }

    let clubResponse: EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>
    let highlightsResponse: EntityResponse<Components.Schemas.ClubHighlightsResponse>
    private(set) var operationIDs: [String] = []

    init(
        clubResponse: EntityResponse<Operations.GetClub.Output.Ok.Body.JsonPayload>,
        highlightsResponse: EntityResponse<Components.Schemas.ClubHighlightsResponse>
    ) {
        self.clubResponse = clubResponse
        self.highlightsResponse = highlightsResponse
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        operationIDs.append(operationID)
        switch operationID {
        case "getClub":
            return try encodedResponse(for: clubResponse)
        case "getClubHighlights":
            return try encodedResponse(for: highlightsResponse)
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
