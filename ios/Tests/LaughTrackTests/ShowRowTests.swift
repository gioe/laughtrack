import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Show row")
struct ShowRowTests {
    @Test("show row uses the highest show-count lineup comedian image")
    func showRowUsesMostPopularLineupComedianImage() {
        let show = makeShow(lineup: [
            lineup(name: "Opening comic", imageURL: "https://example.com/opening.jpg", showCount: 12),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
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
        let parent = lineup(name: "Parent Headliner", imageURL: "https://example.com/parent.jpg", showCount: 60)
        let alias = lineup(name: "Alias Name", imageURL: "https://example.com/alias.jpg", showCount: 5, parentComedian: parent)
        let show = makeShow(lineup: [alias])

        #expect(ShowRow.title(for: show) == "Late show")
        #expect(ShowRow.artworkImageURL(for: show) == "https://example.com/parent.jpg")
    }

    @Test("show row falls back to ticket artwork when lineup is empty")
    func showRowFallsBackToTicketArtworkWhenLineupIsEmpty() {
        let show = makeShow(lineup: [])

        #expect(ShowRow.artworkImageURL(for: show) == nil)
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

    @Test("open mic detection reads the tag list without depending on the show name")
    func openMicDetection() {
        // Deliberately use a non-open-mic name so this asserts the tag-based
        // path, not the name-string fallback. ShowRow + ShowDetailView are
        // driven by the same signal.
        let openMic = makeShow(
            name: "Late Set",
            tags: [.init(slug: "open mic", name: "Open Mic")],
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

    @Test("top lineup picks the three highest-show-count comedians")
    func topLineupPicksMostPopular() {
        let show = makeShow(lineup: [
            lineup(name: "Opener", imageURL: "https://example.com/opener.jpg", showCount: 3),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
            lineup(name: "Filler", imageURL: "https://example.com/filler.jpg", showCount: 1),
        ])

        let top = ShowRow.topLineup(for: show)

        #expect(top.map(\.name) == ["Headliner", "Feature", "Opener"])
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

    @Test("artwork comedian is nil when the most popular performer has no image")
    func artworkComedianNilWhenFeaturedImageMissing() {
        let show = makeShow(lineup: [
            lineup(name: "Headliner", imageURL: "   ", showCount: 50),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 10),
        ])

        #expect(ShowRow.artworkComedian(for: show) == nil)
    }

    @Test("top lineup preserves order when show counts are absent")
    func topLineupPreservesOrderWhenCountsAbsent() {
        let show = makeShow(lineup: [
            lineup(name: "First", imageURL: "https://example.com/first.jpg", showCount: nil),
            lineup(name: "Second", imageURL: "https://example.com/second.jpg", showCount: nil),
        ])

        #expect(ShowRow.topLineup(for: show).map(\.name) == ["First", "Second"])
    }

    @Test("ShowRow.isOpenMic delegates to ShowFormatting on the show name")
    func showRowIsOpenMicMatchesName() {
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

        #expect(ShowRow.priceLabel(for: show) == "$20 - $35")
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
        #expect(ShowRow.previousPriceLabel(for: show) == "$20 - $35")
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
        room: String? = nil,
        tickets: [Components.Schemas.Ticket] = [],
        tags: [Components.Schemas.Tag]? = nil,
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubId: 201,
            clubName: clubName,
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: tickets,
            name: name,
            lineup: lineup,
            tags: tags,
            room: room,
            imageUrl: "https://example.com/show.jpg",
            distanceMiles: 2.1
        )
    }

    private func lineup(
        name: String,
        imageURL: String,
        showCount: Int?,
        parentComedian: Components.Schemas.ComedianLineup? = nil
    ) -> Components.Schemas.ComedianLineup {
        Components.Schemas.ComedianLineup(
            name: name,
            imageUrl: imageURL,
            uuid: UUID().uuidString,
            id: name.utf8.reduce(0) { $0 + Int($1) },
            showCount: showCount,
            parentComedian: parentComedian
        )
    }
}
