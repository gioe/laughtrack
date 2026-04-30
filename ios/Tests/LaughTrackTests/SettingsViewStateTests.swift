#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("Profile settings state")
@MainActor
struct SettingsViewStateTests {
    @Test("Profile reflects saved nearby preference state changes deterministically")
    func profileSettingsStateUpdatesAreDeterministic() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "profile-settings")
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "profile-settings-view")
        let favorites = ComedianFavoriteStore()
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: controller
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)

        controller.applyManualZip("10012", distanceMiles: 50)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbySavedState)
        try host.requireLabel("ZIP 10012")
        try host.requireLabel("50 mi")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsClearButton)

        controller.clear()
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.settingsClearButton) == nil)
    }
}
#endif
