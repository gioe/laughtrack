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

    @Test("show row titles with the highest show-count lineup comedian")
    func showRowUsesMostPopularLineupComedianTitle() {
        let show = makeShow(lineup: [
            lineup(name: "Opening comic", imageURL: "https://example.com/opening.jpg", showCount: 12),
            lineup(name: "Headliner", imageURL: "https://example.com/headliner.jpg", showCount: 42),
            lineup(name: "Feature", imageURL: "https://example.com/feature.jpg", showCount: 20),
        ])

        #expect(ShowRow.title(for: show) == "Headliner")
    }

    @Test("show row titles alias lineup items with the parent comedian")
    func showRowUsesParentComedianForAliasTitle() {
        let parent = lineup(name: "Parent Headliner", imageURL: "https://example.com/parent.jpg", showCount: 60)
        let alias = lineup(name: "Alias Name", imageURL: "https://example.com/alias.jpg", showCount: 5, parentComedian: parent)
        let show = makeShow(lineup: [alias])

        #expect(ShowRow.title(for: show) == "Parent Headliner")
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

    private func makeShow(lineup: [Components.Schemas.ComedianLineup]?) -> Components.Schemas.Show {
        Components.Schemas.Show(
            id: 1,
            clubName: "Comedy Cellar",
            date: Date(timeIntervalSince1970: 1_710_000_000),
            tickets: [],
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
