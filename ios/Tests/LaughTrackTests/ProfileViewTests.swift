#if canImport(UIKit)
import SwiftUI
import Testing
@testable import LaughTrackApp

@Suite("Profile view")
@MainActor
struct ProfileViewTests {
    @Test("profile keeps nearby defaults but adopts compact section framing")
    func profileUsesCompactSectionFraming() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile")
        let nearbyStore = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "shell-profile")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyPreferenceStore: nearbyStore
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environmentObject(ComedianFavoriteStore())
                .environmentObject(authManager)
        )

        try host.requireText("Your comedy setup")
        try host.requireText("Profile")
        try host.requireText("Nearby defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsFavoritesSection)
    }
}
#endif
