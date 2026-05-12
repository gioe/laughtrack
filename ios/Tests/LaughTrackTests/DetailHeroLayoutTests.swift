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

    @Test("show detail replaces lone lineup performer titles with venue title")
    func showDetailReplacesLoneLineupPerformerTitle() {
        var show = Self.showDetail()
        show.name = "Vanessa Jackson"
        show.club = .init(
            id: 301,
            name: "The Broadway Comedy Club",
            address: "318 W. 53rd St, New York, NY",
            imageUrl: "https://example.com/club.png",
            timezone: "America/New_York"
        )
        show.lineup = [
            .init(
                name: "Vanessa Jackson",
                imageUrl: "https://example.com/vanessa.png",
                uuid: "vanessa-jackson",
                id: 401,
                showCount: 1
            )
        ]

        #expect(ShowTitlePresentation.title(for: show) == "Comedy Show at The Broadway Comedy Club")
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

        #expect(facts.map(\.label) == ["When", "Venue", "Distance", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "$30.00")
        #expect(facts.first { $0.label == "Venue" }?.value == "Comedy Cellar")
        #expect(facts.first { $0.label == "Distance" }?.value == "2.1 miles away")
    }

    @Test("show detail summary facts omit missing optional values and address")
    func showSummaryFactsOmitMissingValuesAndAddress() {
        var show = Self.showDetail()
        show.tickets = nil
        show.room = nil
        show.distanceMiles = nil
        show.address = "117 MacDougal St, New York, NY"
        show.club.address = "117 MacDougal St, New York, NY"

        let facts = ShowDetailPresentation.summaryFacts(for: show)

        #expect(facts.map(\.label) == ["When", "Venue", "Tickets"])
        #expect(facts.first { $0.label == "Tickets" }?.value == "Unavailable")
    }

    @Test("show detail ticket cell targets ticket purchase URL")
    func showTicketCellTargetsTicketPurchaseURL() {
        var show = Self.showDetail()
        show.cta = .init(url: "https://laughtrack.app/show-cta", label: "Buy tickets", isSoldOut: false)

        #expect(ShowDetailPresentation.primaryTicketURL(for: show)?.absoluteString == "https://laughtrack.app/tickets")
    }

    @Test("show detail calendar event uses show venue and ticket URL")
    func showCalendarEventUsesShowVenueAndTicketURL() {
        let show = Self.showDetail()

        let event = ShowCalendarEventPresentation.event(for: show)

        #expect(event.title == "Mark Normand and Friends")
        #expect(event.startDate == show.date)
        #expect(event.endDate == show.date.addingTimeInterval(2 * 60 * 60))
        #expect(event.location?.contains("Comedy Cellar") == true)
        #expect(event.url?.absoluteString == "https://laughtrack.app/tickets")
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
