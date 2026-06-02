import Foundation
import Testing
@testable import LaughTrackApp

@Suite("ShowsListView empty-state copy resolver")
struct ShowsListEmptyMessageTests {
    @Test("pinned comedian name produces contextual copy when no filters are active")
    func pinnedComedianYieldsContextualCopy() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: nil
        )
        #expect(message == "Abby Washuta has no upcoming shows on LaughTrack yet.")
    }

    @Test("pinned club name produces contextual copy when no filters are active")
    func pinnedClubYieldsContextualCopy() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: nil,
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(message == "Tribeca Comedy Lounge has no upcoming shows on LaughTrack yet.")
    }

    @Test("search-filter branch is unchanged when a pinned name is set")
    func searchFilterBranchUnchanged() {
        let withComedianSearch = ShowsListEmptyMessage.resolve(
            comedianSearchText: "Mark Normand",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: nil,
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(
            withComedianSearch ==
                "No shows matched this search. Try another comedian, club, or a broader date range."
        )

        let withClubSearch = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "Comedy Cellar",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: nil
        )
        #expect(
            withClubSearch ==
                "No shows matched this search. Try another comedian, club, or a broader date range."
        )
    }

    @Test("ZIP-filter branch is unchanged when a pinned name is set")
    func zipFilterBranchUnchanged() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: true,
            pinnedComedianName: nil,
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(
            message ==
                "No shows matched this ZIP code yet. Broaden the radius or clear location filters."
        )
    }

    @Test("comedian name wins over club name when both are present")
    func comedianNamePrecedesClubName() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(message == "Abby Washuta has no upcoming shows on LaughTrack yet.")
    }

    @Test("whitespace-only pinned name falls back to generic copy")
    func whitespaceOnlyPinnedNameFallsBack() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "   ",
            pinnedClubName: nil
        )
        #expect(message == "No shows are available right now.")
    }

    @Test("no pinned name and no filters produces generic copy")
    func unpinnedNoFiltersIsGeneric() {
        let message = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: nil,
            pinnedClubName: nil
        )
        #expect(message == "No shows are available right now.")
    }
}
