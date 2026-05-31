import Foundation
import Testing
import LaughTrackAPIClient
@testable import LaughTrackApp

/// Authoritative test suite for `ShowTitlePresentation.title(for:)`.
///
/// Both the `Show` and `ShowDetail` overloads share the same `displayTitle`
/// logic, so every title-rendering assertion (plain passthrough, solo-headliner
/// "<Performer> Headlines", performer-looking fallback, named-show preservation)
/// lives here — and only here. Do **not** re-encode these expectations in
/// ShowRowTests or DetailHeroLayoutTests: a behavior change to the title format
/// must have a single place to update. The duplicated solo-headliner fixture
/// across ShowRowTests + DetailHeroLayoutTests is exactly what shipped a stale
/// expectation in 7045f4bf8 (fixed reactively in TASK-2536); see TASK-2537.
@Suite("Show title presentation")
struct ShowTitlePresentationTests {
    // MARK: - Show overload

    @Test("passes a plain show name through unchanged")
    func passesPlainShowNameThrough() {
        let show = makeShow(name: "Late show", lineup: [
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42)
        ])

        #expect(ShowTitlePresentation.title(for: show) == "Late show")
    }

    @Test("turns a lone lineup performer title into a headline title")
    func turnsLoneLineupPerformerIntoHeadline() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: [
                lineup(name: "Vanessa Jackson", imageURL: "https://example.com/vanessa.jpg", showCount: 4)
            ]
        )

        #expect(ShowTitlePresentation.title(for: show) == "Vanessa Jackson Headlines")
    }

    @Test("falls back to a venue title for performer-looking titles when lineup is absent")
    func fallsBackToVenueTitleForPerformerLookingTitleWithoutLineup() {
        let show = makeShow(
            name: "Vanessa Jackson",
            clubName: "The Broadway Comedy Club",
            lineup: nil
        )

        #expect(ShowTitlePresentation.title(for: show) == "Comedy Show at The Broadway Comedy Club")
    }

    @Test("falls back to a venue title when the show name is empty")
    func fallsBackToVenueTitleWhenNameEmpty() {
        let show = makeShow(
            name: "",
            clubName: "The Broadway Comedy Club",
            lineup: nil
        )

        #expect(ShowTitlePresentation.title(for: show) == "Comedy Show at The Broadway Comedy Club")
    }

    @Test("preserves titled shows that contain show words")
    func preservesNamedShows() {
        let show = makeShow(
            name: "Atsuko Late Set",
            clubName: "The Stand",
            lineup: nil
        )

        #expect(ShowTitlePresentation.title(for: show) == "Atsuko Late Set")
    }

    @Test("preserves longer production titles")
    func preservesLongerProductionTitles() {
        let show = makeShow(
            name: "Comedy Show at The Grisly Pear Midtown",
            clubName: "The Grisly Pear Midtown",
            lineup: nil
        )

        #expect(ShowTitlePresentation.title(for: show) == "Comedy Show at The Grisly Pear Midtown")
    }

    // MARK: - ShowDetail overload (same display logic, different input type)

    @Test("show detail turns a lone lineup performer title into a headline title")
    func showDetailTurnsLoneLineupPerformerIntoHeadline() {
        var show = makeShowDetail()
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

        #expect(ShowTitlePresentation.title(for: show) == "Vanessa Jackson Headlines")
    }

    @Test("show detail passes a plain show name through unchanged")
    func showDetailPassesPlainNameThrough() {
        let show = makeShowDetail()

        #expect(ShowTitlePresentation.title(for: show) == "Mark Normand and Friends")
    }

    // MARK: - Fixtures

    private func makeShow(
        name: String = "Late show",
        clubName: String = "Comedy Cellar",
        lineup: [Components.Schemas.ComedianLineup]?
    ) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubId: 201,
            clubName: clubName,
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: [],
            name: name,
            lineup: lineup,
            room: nil,
            imageUrl: "https://example.com/show.jpg",
            distanceMiles: 2.1
        )
    }

    private func lineup(
        name: String,
        imageURL: String,
        showCount: Int?
    ) -> Components.Schemas.ComedianLineup {
        Components.Schemas.ComedianLineup(
            name: name,
            imageUrl: imageURL,
            uuid: UUID().uuidString,
            id: name.utf8.reduce(0) { $0 + Int($1) },
            showCount: showCount
        )
    }

    private func makeShowDetail() -> Components.Schemas.ShowDetail {
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
