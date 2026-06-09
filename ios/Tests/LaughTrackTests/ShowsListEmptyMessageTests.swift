import Foundation
import Testing
@testable import LaughTrackApp

@Suite("ShowsListView empty-state copy resolver")
struct ShowsListEmptyMessageTests {
    @Test("pinned comedian falls into the broaden-filters branch with a Clear filters action")
    func pinnedComedianYieldsBroadenFiltersCopy() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: nil
        )
        #expect(resolution.title == "No matching shows")
        #expect(
            resolution.message ==
                "Try broadening your location or date range to see more shows from Abby Washuta."
        )
        #expect(resolution.actionTitle == "Clear filters")
    }

    @Test("pinned club uses the same broaden-filters copy and Clear filters action")
    func pinnedClubYieldsBroadenFiltersCopy() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: nil,
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(resolution.title == "No matching shows")
        #expect(
            resolution.message ==
                "Try broadening your location or date range to see more shows from Tribeca Comedy Lounge."
        )
        #expect(resolution.actionTitle == "Clear filters")
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
        #expect(withComedianSearch.title == "No shows yet")
        #expect(
            withComedianSearch.message ==
                "No shows matched this search. Try another comedian, club, or a broader date range."
        )
        #expect(withComedianSearch.actionTitle == nil)

        let withClubSearch = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "Comedy Cellar",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: nil
        )
        #expect(withClubSearch.title == "No shows yet")
        #expect(
            withClubSearch.message ==
                "No shows matched this search. Try another comedian, club, or a broader date range."
        )
        #expect(withClubSearch.actionTitle == nil)
    }

    @Test("ZIP-filter branch is unchanged when a pinned name is set")
    func zipFilterBranchUnchanged() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: true,
            pinnedComedianName: nil,
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(resolution.title == "No shows yet")
        #expect(
            resolution.message ==
                "No shows matched this ZIP code yet. Broaden the radius or clear location filters."
        )
        #expect(resolution.actionTitle == nil)
    }

    @Test("comedian name wins over club name when both are present")
    func comedianNamePrecedesClubName() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "Abby Washuta",
            pinnedClubName: "Tribeca Comedy Lounge"
        )
        #expect(resolution.title == "No matching shows")
        #expect(
            resolution.message ==
                "Try broadening your location or date range to see more shows from Abby Washuta."
        )
        #expect(resolution.actionTitle == "Clear filters")
    }

    @Test("whitespace-only pinned name falls back to generic copy")
    func whitespaceOnlyPinnedNameFallsBack() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: "   ",
            pinnedClubName: nil
        )
        #expect(resolution.title == "No shows yet")
        #expect(resolution.message == "No shows are available right now.")
        #expect(resolution.actionTitle == nil)
    }

    @Test("no pinned name and no filters produces generic copy")
    func unpinnedNoFiltersIsGeneric() {
        let resolution = ShowsListEmptyMessage.resolve(
            comedianSearchText: "",
            clubSearchText: "",
            hasActiveNearbyPreference: false,
            pinnedComedianName: nil,
            pinnedClubName: nil
        )
        #expect(resolution.title == "No shows yet")
        #expect(resolution.message == "No shows are available right now.")
        #expect(resolution.actionTitle == nil)
    }
}
