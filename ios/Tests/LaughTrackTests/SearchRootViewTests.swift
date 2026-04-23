import SwiftUI
import Testing
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
}
