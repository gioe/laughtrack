import SwiftUI
import Testing
import LaughTrackCore
@testable import LaughTrackApp

#if canImport(UIKit)
@Suite("Search root")
@MainActor
struct SearchRootViewTests {
    @Test("search root defaults to shows pivot")
    func defaultsToShows() async throws {
        let host = HostedView(
            SearchRootView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "search-root-default")
            )
            .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Shows")
        try host.requireView(withIdentifier: LaughTrackViewTestID.showsSearchScreen)
    }
}
#endif

@Suite("Search root model")
@MainActor
struct SearchRootModelTests {
    @Test("switching pivots does not navigate away from search root")
    func switchingPivotsStaysInPlace() async throws {
        let model = SearchRootModel()
        #expect(model.activePivot == .shows)
        model.activePivot = .clubs
        #expect(model.activePivot == .clubs)
    }

    @Test("root query is applied to the active pivot model")
    func rootQueryAppliesToActivePivotModel() async throws {
        let model = SearchRootModel()
        let showsModel = ShowsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: NearbyPreferenceStore(),
                resolver: LaughTrackCore.CurrentLocationZipResolver()
            )
        )
        let clubsModel = ClubsDiscoveryModel()
        let comediansModel = ComediansDiscoveryModel()

        model.query = "Comedy Cellar"
        model.activePivot = .clubs
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(comediansModel.searchText == "")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Atsuko"
        model.activePivot = .comedians
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(comediansModel.searchText == "Atsuko")
        #expect(clubsModel.searchText == "Comedy Cellar")
        #expect(showsModel.comedianSearchText == "")

        model.query = "Mark Normand"
        model.activePivot = .shows
        model.applyQuery(
            showsModel: showsModel,
            comediansModel: comediansModel,
            clubsModel: clubsModel
        )
        #expect(showsModel.comedianSearchText == "Mark Normand")
        #expect(showsModel.clubSearchText == "")
    }
}
