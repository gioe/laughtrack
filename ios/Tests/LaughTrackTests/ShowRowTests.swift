import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Show row")
@MainActor
struct ShowRowTests {
    @Test("show row exposes a compact paper ticket presentation for home rails")
    func showRowExposesCompactPaperTicketPresentationForHomeRails() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(source.contains("enum ShowRowPresentation"))
        #expect(source.contains("case standard"))
        #expect(source.contains("case compactTicket"))
        #expect(source.contains("case compactTicketProminent"))
        #expect(source.contains("let presentation: ShowRowPresentation"))
        #expect(source.contains("presentation: ShowRowPresentation = .standard"))
        #expect(source.contains("private var ticketPaper"))
        #expect(source.contains("private var ticketInk"))
        #expect(source.contains("private var ticketInkMuted"))
        #expect(source.contains("private var ticketBorder"))
        #expect(source.contains("private var ticketStubBackground"))
        #expect(source.contains("private var ticketEdgeAccent"))
        #expect(source.contains("case .compactTicket"))
    }

    @Test("show row does not render proximity badges")
    func showRowDoesNotRenderProximityBadges() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(!source.contains("Near you"))
        #expect(!source.contains("nearbyRadiusMiles"))
    }

    @Test("show row prefers lineup popularity over historical show count for artwork")
    func showRowUsesMostPopularLineupComedianImage() {
        let show = makeShow(lineup: [
            lineup(name: "Opening comic", imageURL: "https://example.com/opening.jpg", showCount: 120, popularity: 12),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 4, popularity: 95),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20, popularity: 30),
        ])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/headliner.jpg")
    }

    // Title-transformation behavior (plain passthrough, solo-headliner "<Performer>
    // Headlines", performer-looking fallback, named-show preservation) is owned by
    // ShowTitlePresentationTests — the single authoritative suite. ShowRow.title is a
    // thin passthrough, so we assert delegation rather than re-encoding the expected
    // strings here (see TASK-2537).
    @Test("show row title delegates to ShowTitlePresentation")
    func showRowTitleDelegatesToPresentation() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: [
                lineup(name: "Vanessa Jackson", imageURL: "https://example.com/vanessa.jpg", showCount: 4)
            ]
        )

        #expect(ShowRow.title(for: show) == ShowTitlePresentation.title(for: show))
    }

    @Test("show row list title passes non-venue titles through unchanged")
    func showRowListTitlePassesThroughNonVenueTitles() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: [
                lineup(name: "Vanessa Jackson", imageURL: "https://example.com/vanessa.jpg", showCount: 4)
            ]
        )

        // listTitle only collapses the "Comedy Show at <club>" venue fallback;
        // every other title (headline titles included) is passed through verbatim.
        #expect(ShowRow.listTitle(for: show) == ShowTitlePresentation.title(for: show))
    }

    @Test("show row collapses the venue fallback title in the compact list title")
    func showRowCollapsesVenueFallbackInCompactListTitle() {
        let show = makeShow(
            name: "",
            clubName: "The Broadway Comedy Club",
            lineup: nil
        )

        // The venue-fallback title itself is covered in ShowTitlePresentationTests;
        // here we assert ShowRow's own collapse of that fallback to "Comedy show".
        #expect(ShowRow.listTitle(for: show) == "Comedy show")
    }

    @Test("show row keeps named shows in compact list title")
    func showRowKeepsNamedShowsInCompactListTitle() {
        let show = makeShow(
            name: "Golden Gate Comedy Night",
            clubName: "The Function SF",
            lineup: nil
        )

        #expect(ShowRow.listTitle(for: show) == "Golden Gate Comedy Night")
    }

    @Test("artwork-backed rows preserve distinct event titles for the same headliner")
    func artworkBackedRowsPreserveDistinctEventTitlesForSameHeadliner() {
        let sharedHeadliner = lineup(
            name: "Shared Headliner",
            imageURL: "https://example.com/shared-headliner.jpg",
            showCount: 42
        )
        let fridayShow = makeShow(
            name: "Friday Night Showcase",
            lineup: [sharedHeadliner]
        )
        let saturdayShow = makeShow(
            name: "Saturday Night Showcase",
            lineup: [sharedHeadliner]
        )

        #expect(ShowRow.primaryListTitle(for: fridayShow, headliner: sharedHeadliner) == "Friday Night Showcase")
        #expect(ShowRow.primaryListTitle(for: saturdayShow, headliner: sharedHeadliner) == "Saturday Night Showcase")
        #expect(ShowRow.headlinerContext(for: fridayShow, headliner: sharedHeadliner) == "Shared Headliner")
        #expect(ShowRow.headlinerContext(for: saturdayShow, headliner: sharedHeadliner) == "Shared Headliner")
    }

    @Test("artwork-backed rows keep the performer primary for unnamed shows")
    func artworkBackedRowsKeepPerformerPrimaryForUnnamedShows() {
        let headliner = lineup(
            name: "Featured Comic",
            imageURL: "https://example.com/featured-comic.jpg",
            showCount: 20
        )
        let show = makeShow(name: "", clubName: "", lineup: [headliner])

        #expect(ShowRow.primaryListTitle(for: show, headliner: headliner) == "Featured Comic")
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == nil)
    }

    @Test("artwork-backed rows keep the performer primary for venue-fallback shows")
    func artworkBackedRowsKeepPerformerPrimaryForVenueFallbackShows() {
        let headliner = lineup(
            name: "Featured Comic",
            imageURL: "https://example.com/featured-comic.jpg",
            showCount: 20
        )
        let show = makeShow(
            name: "",
            clubName: "The Broadway Comedy Club",
            lineup: [headliner]
        )

        #expect(ShowRow.listTitle(for: show) == "Comedy show")
        #expect(ShowRow.primaryListTitle(for: show, headliner: headliner) == "Featured Comic")
        #expect(ShowRow.headlinerContext(for: show, headliner: headliner) == nil)
        #expect(ShowRow.venueLine(for: show) == "The Broadway Comedy Club")
    }

    @Test("headliner block uses the event-first title presentation")
    func headlinerBlockUsesEventFirstTitlePresentation() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(source.contains("Text(Self.primaryListTitle(for: show, headliner: headliner))"))
        #expect(source.contains("Self.headlinerContext(for: show, headliner: headliner)"))
    }

    @Test("show row venue line includes city and state when available")
    func showRowVenueLineIncludesCityAndState() {
        let show = makeShow(
            clubName: "The Grisly Pear Greenwich Village",
            clubCity: "New York",
            clubState: "NY",
            lineup: []
        )

        #expect(ShowRow.venueLine(for: show) == "The Grisly Pear Greenwich Village • New York, NY")
    }

    @Test("show row venue line falls back to club name without location")
    func showRowVenueLineFallsBackToClubNameWithoutLocation() {
        let show = makeShow(
            clubName: "The Grisly Pear Greenwich Village",
            clubCity: nil,
            clubState: nil,
            lineup: []
        )

        #expect(ShowRow.venueLine(for: show) == "The Grisly Pear Greenwich Village")
    }

    @Test("show row preserves longer production titles")
    func showRowPreservesLongerProductionTitles() {
        let show = makeShow(
            name: "Comedy Show at The Grisly Pear Midtown",
            clubName: "The Grisly Pear Midtown",
            lineup: nil
        )

        #expect(ShowRow.title(for: show) == "Comedy Show at The Grisly Pear Midtown")
    }

    @Test("show row keeps parent comedian artwork for alias lineup items")
    func showRowUsesParentComedianForAliasArtwork() {
        let parent = lineup(
            name: "Parent Headliner",
            imageURL: "https://example.com/parent.jpg",
            showCount: 5,
            popularity: 90
        )
        let alias = lineup(
            name: "Alias Name",
            imageURL: "https://example.com/alias.jpg",
            showCount: 50,
            popularity: 1,
            parentComedian: parent
        )
        let other = lineup(
            name: "Other Comic",
            imageURL: "https://example.com/other.jpg",
            showCount: 80,
            popularity: 40
        )
        let show = makeShow(lineup: [alias, other])

        #expect(ShowRow.title(for: show) == "Late show")
        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/parent.jpg")
    }

    @Test("show row falls back to absolute show artwork when lineup is empty")
    func showRowFallsBackToTicketArtworkWhenLineupIsEmpty() {
        let show = makeShow(lineup: [])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/show.jpg")
    }

    @Test("show row ignores relative show artwork placeholders")
    func showRowIgnoresRelativeShowArtworkPlaceholders() {
        let show = makeShow(imageURL: "/placeholders/club-placeholder.svg", lineup: [])

        #expect(ShowRow.artworkImageURL(for: show) == nil)
    }

    @Test("show row uses a stable branded artwork slot")
    func showRowUsesStableBrandedArtworkSlot() throws {
        let source = try String(contentsOf: showRowSourceURL(), encoding: .utf8)

        #expect(ShowRow.artworkSlotSize == 60)
        #expect(source.contains("private var artworkSlot"))
        #expect(source.contains("Image(systemName: ArtworkFallbackKind.show.systemImage)"))
        #expect(source.components(separatedBy: "artworkSlot").count >= 4)
    }

    @Test("show row uses the first lineup image when popularity counts are absent")
    func showRowUsesFirstLineupImageWhenPopularityCountsAreAbsent() {
        let show = makeShow(lineup: [
            lineup(name: "First comic", imageURL: "https://example.com/first.jpg", showCount: nil),
            lineup(name: "Second comic", imageURL: "https://example.com/second.jpg", showCount: nil),
        ])

        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/first.jpg")
    }

    @Test("list dates use the supplied venue timezone")
    func listDatesUseSuppliedVenueTimezone() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)

        #expect(ShowFormatting.listDate(date, timezoneID: "America/New_York").contains("8:00"))
        #expect(ShowFormatting.listDate(date, timezoneID: "America/Los_Angeles").contains("5:00"))
    }

    @Test("date stack returns weekday, day, and time in the venue timezone")
    func dateStackReturnsComponentsInVenueTimezone() {
        // 2024-05-04 00:00:00 UTC → 2024-05-03 20:00 ET → Friday the 3rd
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(date, timezoneID: "America/New_York")

        #expect(stack.weekday == "FRI")
        #expect(stack.day == "3")
        #expect(stack.time.contains("8:00"))
    }

    @Test("date stack appends timezone abbreviation when venue timezone differs from device timezone")
    func dateStackAppendsRemoteTimezoneAbbreviation() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(
            date,
            timezoneID: "America/Los_Angeles",
            localTimezone: TimeZone(identifier: "America/New_York")!
        )

        #expect(stack.time.contains("5:00"))
        #expect(stack.time.contains("PDT"))
    }

    @Test("date stack omits timezone abbreviation when venue timezone matches device timezone")
    func dateStackOmitsLocalTimezoneAbbreviation() {
        let date = Date(timeIntervalSince1970: 1_714_780_800)
        let stack = ShowFormatting.dateStack(
            date,
            timezoneID: "America/New_York",
            localTimezone: TimeZone(identifier: "America/New_York")!
        )

        #expect(stack.time.contains("8:00"))
        #expect(!stack.time.contains("EDT"))
    }

    @Test("open mic detection reads the tag list without depending on the show name")
    func openMicDetection() {
        // Deliberately use a non-open-mic name so this asserts the tag-based
        // path, not the name-string fallback. ShowRow + ShowDetailView are
        // driven by the same signal.
        let openMic = makeShow(
            name: "Late Set",
            tags: [.init(slug: "open-mic", name: "Open Mic")],
            lineup: nil
        )
        #expect(ShowRow.isOpenMic(openMic))

        let nonOpenMic = makeShow(
            name: "Late Set",
            tags: [.init(slug: "weekly-showcase", name: "Weekly Showcase")],
            lineup: nil
        )
        #expect(ShowRow.isOpenMic(nonOpenMic) == false)

        let untagged = makeShow(name: "Late Set", tags: nil, lineup: nil)
        #expect(ShowRow.isOpenMic(untagged) == false)
    }

    @Test("name-based open mic fallback still recognizes common name variants")
    func openMicNameFallback() {
        // Defensive fallback for venues whose tag list hasn't been backfilled
        // yet — the function is intentionally retained on ShowFormatting.
        #expect(ShowFormatting.isOpenMic("Tuesday Open Mic"))
        #expect(ShowFormatting.isOpenMic("OPEN MIC"))
        #expect(ShowFormatting.isOpenMic("Comedy open-mic night"))
        #expect(ShowFormatting.isOpenMic("Atsuko Late Set") == false)
        #expect(ShowFormatting.isOpenMic(nil) == false)
    }

    @Test("top lineup ranks by popularity, then show count, then lineup order")
    func topLineupPicksMostPopular() {
        let show = makeShow(lineup: [
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 3, popularity: 20),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 2, popularity: 90),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20, popularity: 20),
            lineup(name: "Filler", imageURL: "https://example.com/filler.jpg", showCount: 20, popularity: 20),
        ])

        let top = ShowRow.topLineup(for: show)

        #expect(top.map(\.name) == ["Headliner", "Feature", "Filler"])
    }

    @Test("top lineup excludes the artwork comedian to avoid duplicate avatars")
    func topLineupExcludesArtworkComedian() {
        let show = makeShow(lineup: [
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 3),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
            lineup(name: "Filler", imageURL: "https://example.com/filler.jpg", showCount: 1),
        ])

        let artwork = ShowRow.artworkComedian(for: show)
        #expect(artwork?.name == "Headliner")
        #expect(ShowRow.topLineup(for: show, excluding: artwork).map(\.name) == ["Feature", "Opener", "Filler"])
    }

    @Test("supporting lineup preserves performers beyond the three-avatar limit")
    func supportingLineupPreservesOverflowPerformers() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 50),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 40),
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 30),
            lineup(name: "Guest", imageURL: "https://example.com/guest.jpg", showCount: 20),
            lineup(name: "Host", imageURL: "https://example.com/host.jpg", showCount: 10),
        ])

        let headliner = ShowRow.artworkComedian(for: show)
        let supporting = ShowRow.supportingLineup(for: show, excluding: headliner)

        #expect(supporting.map(\.name) == ["Feature", "Opener", "Guest", "Host"])
        #expect(ShowRow.supportingLabel(for: supporting) == "with Feature, Opener, Guest +1 more")
    }

    @Test("supporting lineup preserves performers at the three-avatar limit")
    func supportingLineupPreservesPerformersAtVisibleLimit() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 40),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 30),
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 20),
            lineup(name: "Host", imageURL: "https://example.com/host.jpg", showCount: 10),
        ])

        let headliner = ShowRow.artworkComedian(for: show)
        let supporting = ShowRow.supportingLineup(for: show, excluding: headliner)

        #expect(supporting.map(\.name) == ["Feature", "Opener", "Host"])
        #expect(ShowRow.supportingLabel(for: supporting) == "with Feature, Opener, Host")
    }

    @Test("artwork comedian skips a more popular performer without absolute artwork")
    func artworkComedianSkipsFeaturedPerformerWithoutAbsoluteArtwork() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "/relative/headliner.jpg", showCount: 50, popularity: 100),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 10, popularity: 10),
        ])

        #expect(ShowRow.artworkComedian(for: show)?.name == "Feature")
        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/feature.jpg")
    }

    @Test("top lineup preserves order when show counts are absent")
    func topLineupPreservesOrderWhenCountsAbsent() {
        let show = makeShow(lineup: [
            lineup(name: "First", imageURL: "https://example.com/first.jpg", showCount: nil),
            lineup(name: "Second", imageURL: "https://example.com/second.jpg", showCount: nil),
        ])

        #expect(ShowRow.topLineup(for: show).map(\.name) == ["First", "Second"])
    }

    @Test("ShowRow.isOpenMic falls back to the show name when no tags are present")
    func showRowIsOpenMicMatchesName() {
        // Tags omitted on the fixture so this exercises the name-string
        // fallback path inside `ShowRow.isOpenMic`.
        let show = makeShow(name: "Tuesday Open Mic", lineup: nil)
        #expect(ShowRow.isOpenMic(show))
    }

    @Test("show row formats a single ticket price")
    func showRowFormatsSingleTicketPrice() {
        let show = makeShow(
            tickets: [.init(price: 24, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission")],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "$24")
    }

    @Test("show row formats a ticket price range")
    func showRowFormatsTicketPriceRange() {
        let show = makeShow(
            tickets: [
                .init(price: 35, purchaseUrl: "https://example.com/vip", soldOut: false, _type: "VIP"),
                .init(price: 20, purchaseUrl: "https://example.com/ga", soldOut: false, _type: "General admission"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "From $20")
    }

    @Test("show row formats free tickets")
    func showRowFormatsFreeTickets() {
        let show = makeShow(
            tickets: [.init(price: 0, purchaseUrl: "https://example.com/free", soldOut: false, _type: "RSVP")],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == "Free")
    }

    @Test("show row omits price when no available ticket has a price")
    func showRowOmitsUnavailablePrice() {
        let show = makeShow(
            tickets: [
                .init(price: nil, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission"),
                .init(price: 50, purchaseUrl: "https://example.com/sold-out", soldOut: true, _type: "VIP"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == nil)
    }

    @Test("previous price label exposes the price of every-ticket-sold-out shows for strikethrough")
    func previousPriceLabelExposesAllSoldOutPrice() {
        let show = makeShow(
            tickets: [
                .init(price: 20, purchaseUrl: "https://example.com/ga", soldOut: true, _type: "General admission"),
                .init(price: 35, purchaseUrl: "https://example.com/vip", soldOut: true, _type: "VIP"),
            ],
            lineup: []
        )

        #expect(ShowRow.priceLabel(for: show) == nil)
        #expect(ShowRow.previousPriceLabel(for: show) == "From $20")
    }

    @Test("previous price label matches priceLabel when tickets are still available")
    func previousPriceLabelMatchesAvailableTickets() {
        let show = makeShow(
            tickets: [
                .init(price: 24, purchaseUrl: "https://example.com/tickets", soldOut: false, _type: "General admission"),
            ],
            lineup: []
        )

        #expect(ShowRow.previousPriceLabel(for: show) == ShowRow.priceLabel(for: show))
    }

    @Test("previous price label is nil when the show has no tickets at all")
    func previousPriceLabelNilWhenNoTickets() {
        let show = makeShow(tickets: [], lineup: [])

        #expect(ShowRow.previousPriceLabel(for: show) == nil)
    }

    @Test("show row exposes a trimmed room label")
    func showRowExposesTrimmedRoomLabel() {
        let show = makeShow(room: "  Village Underground  ", lineup: [])

        #expect(ShowRow.roomLabel(for: show) == "Village Underground")
    }

    @Test("show row omits blank room labels")
    func showRowOmitsBlankRoomLabels() {
        let show = makeShow(room: "   ", lineup: [])

        #expect(ShowRow.roomLabel(for: show) == nil)
    }

    @Test("show row omits room labels that duplicate the club name")
    func showRowOmitsRoomDuplicatingClubName() {
        let show = makeShow(
            clubName: "Punch Line Philly",
            room: "  punch line PHILLY ",
            lineup: []
        )

        #expect(ShowRow.roomLabel(for: show) == nil)
    }

    @Test("show row keeps room labels distinct from the club name")
    func showRowKeepsDistinctRoomLabels() {
        let show = makeShow(
            clubName: "Comedy Cellar",
            room: "Village Underground",
            lineup: []
        )

        #expect(ShowRow.roomLabel(for: show) == "Village Underground")
    }

    @Test("show row metadata keeps the date visible after artwork leads the row")
    func showRowMetadataKeepsDateVisible() {
        let show = makeShow(room: "Main Room", lineup: [])
        let metadata = ShowRow.metadata(for: show)

        #expect(metadata.first == ShowFormatting.listDate(show.date, timezoneID: show.timezone))
        #expect(metadata.contains("Main Room"))
    }

    private func makeShow(
        name: String = "Late show",
        clubName: String = "Comedy Cellar",
        clubCity: String? = nil,
        clubState: String? = nil,
        room: String? = nil,
        tickets: [Components.Schemas.Ticket] = [],
        tags: [Components.Schemas.Tag]? = nil,
        imageURL: String = "https://example.com/show.jpg",
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubId: 201,
            clubName: clubName,
            clubCity: clubCity,
            clubState: clubState,
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: tickets,
            name: name,
            lineup: lineup,
            tags: tags,
            room: room,
            imageUrl: imageURL,
            distanceMiles: 2.1
        )
    }

    private func lineup(
        name: String,
        imageURL: String,
        showCount: Int?,
        popularity: Double? = nil,
        parentComedian: Components.Schemas.ComedianLineup? = nil
    ) -> Components.Schemas.ComedianLineup {
        let id = name.utf8.reduce(0) { $0 + Int($1) }
        return Components.Schemas.ComedianLineup(
            name: name,
            imageUrl: imageURL,
            uuid: UUID().uuidString,
            id: id,
            socialData: popularity.map { .init(id: id, popularity: $0) },
            showCount: showCount,
            parentComedian: parentComedian
        )
    }

    private func showRowSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Components/ShowRow.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}
