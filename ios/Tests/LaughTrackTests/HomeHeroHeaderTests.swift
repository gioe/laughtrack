#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Home hero header")
@MainActor
struct HomeHeroHeaderTests {
    @Test("renders 'What's funny near {City, ST}?' when a saved Nearby preference carries city and state")
    func locationAwareHeader() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "hero-located")
        store.setGeolocatedZip("10012", distanceMiles: 25, city: "New York", state: "NY")

        let host = HostedView(
            HomeHeroHeader(nearbyPreferenceStore: store)
                .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("What's funny near New York, NY?")
    }

    @Test("preserves the static fallback header when no Nearby preference is set")
    func staticFallbackHeader() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "hero-fallback")

        let host = HostedView(
            HomeHeroHeader(nearbyPreferenceStore: store)
                .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Comedy worth noticing nearby")
    }

    @Test("renders 'What's funny near {City, ST}?' after manual-ZIP refinement resolves city/state")
    func locationAwareHeaderAfterManualZipRefinement() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "hero-manual-refined")
        let zipResolver = StubZipLocationResolver(
            result: .success(ResolvedNearbyLocation(zipCode: "60614", city: "Chicago", state: "IL"))
        )
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(
            store: store,
            zipLocationResolver: zipResolver
        )

        _ = controller.applyManualZip("60614", distanceMiles: 25)
        await controller.pendingZipRefinement?.value

        let host = HostedView(
            HomeHeroHeader(nearbyPreferenceStore: store)
                .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("What's funny near Chicago, IL?")
    }
}
#endif
