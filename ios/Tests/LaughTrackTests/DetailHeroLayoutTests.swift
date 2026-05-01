import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

@Suite("Detail hero layout")
struct DetailHeroLayoutTests {
    @Test("detail hero keeps media landscape and below most of a phone viewport")
    func detailHeroUsesCompactLandscapeMedia() {
        #expect(DetailHeroLayout.imageAspectRatio >= 1.45)
        #expect(DetailHeroLayout.maximumMediaHeight <= 280)
        #expect(DetailHeroLayout.mediaHeight(forWidth: 390) <= 280)
    }

    @Test("detail hero action layout stays compact enough for title clearance")
    func detailHeroActionLayoutIsCompact() {
        #expect(DetailHeroLayout.actionDiameter <= 40)
        #expect(DetailHeroLayout.actionLabelVerticalGap <= 3)
        #expect(DetailHeroLayout.contentSpacingWithActions <= 8)
    }

    @Test("club detail hero omits subtitle copy")
    func clubDetailHeroOmitsSubtitleCopy() {
        #expect(ClubDetailHeroPresentation.subtitle(upcomingShowCount: 8, zipCode: "10012") == nil)
        #expect(ClubDetailHeroPresentation.subtitle(upcomingShowCount: 0, zipCode: "10012") == nil)
    }

    @Test("show detail hero does not duplicate summary facts")
    func showHeroBadgesAreEmpty() {
        let show = Self.showDetail()

        #expect(ShowDetailPresentation.heroBadges(for: show).isEmpty)
    }

    @Test("show detail summary facts include event operations")
    func showSummaryFactsIncludeOperationalDetails() {
        let show = Self.showDetail()

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Tickets", "Venue", "Room", "Distance", "Address"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "$30.00")
        #expect(facts.first { $0.label == "Venue" }?.value == "Comedy Cellar")
        #expect(facts.first { $0.label == "Distance" }?.value == "2.1 miles away")
    }

    @Test("show detail summary facts omit missing optional values")
    func showSummaryFactsOmitMissingValues() {
        var show = Self.showDetail()
        show.tickets = nil
        show.room = nil
        show.distanceMiles = nil
        show.address = nil
        show.club.address = nil

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Tickets", "Venue"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "Unavailable")
    }

    @Test("show detail ticket subtitle uses user-facing copy")
    func showTicketSubtitleIsUserFacing() {
        let show = Self.showDetail()

        #expect(ShowDetailPresentation.ticketSubtitle(for: show) == "Choose a ticket option or open the venue checkout.")
    }

    @Test("show detail omits editor note section")
    func showDetailOmitsEditorNoteSection() {
        let show = Self.showDetail()

        #expect(ShowDetailPresentation.shouldShowEditorNote(for: show) == false)
    }

    private static func showDetail() -> Components.Schemas.ShowDetail {
        .init(
            id: 301,
            clubName: "Comedy Cellar",
            date: Date(timeIntervalSince1970: 1_779_705_000),
            tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/tickets", soldOut: false, _type: "General admission")],
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: nil,
            description: nil,
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show.png",
            soldOut: false,
            distanceMiles: 2.1,
            timezone: "America/New_York",
            showPageUrl: "https://laughtrack.app/show",
            club: .init(
                id: 201,
                name: "Comedy Cellar",
                address: "117 MacDougal St, New York, NY",
                imageUrl: "https://example.com/club.png",
                timezone: "America/New_York"
            ),
            cta: .init(url: "https://laughtrack.app/tickets", label: "Buy tickets", isSoldOut: false)
        )
    }
}
