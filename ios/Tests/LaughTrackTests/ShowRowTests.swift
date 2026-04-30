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

    @Test("show row titles with the show name")
    func showRowUsesShowNameTitle() {
        let show = makeShow(lineup: [
            lineup(name: "Opening comic", imageURL: "https://example.com/opening.jpg", showCount: 12),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
        ])

        #expect(ShowRow.title(for: show) == "Late show")
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

    private func makeShow(
        tickets: [Components.Schemas.Ticket] = [],
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubName: "Comedy Cellar",
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: tickets,
            name: "Late show",
            lineup: lineup,
            imageUrl: "https://example.com/show.jpg"
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
