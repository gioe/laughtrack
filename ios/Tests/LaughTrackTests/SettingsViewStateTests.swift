#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("SettingsView state")
@MainActor
struct SettingsViewStateTests {
    @Test("Settings screen reflects saved nearby preference state changes deterministically")
    func settingsStateUpdatesAreDeterministic() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "settings")
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
        let model = SettingsNearbyPreferenceModel(nearbyLocationController: controller)
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "settings-view")
        let favorites = ComedianFavoriteStore()
        let host = HostedView(
            SettingsView(
                signedOutMessage: nil,
                nearbyLocationController: controller,
                model: model
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)

        model.zipCodeDraft = "10012"
        model.distanceMiles = 50
        model.saveNearbyPreference()
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbySavedState)
        try host.requireLabel("ZIP 10012")
        try host.requireLabel("50 mi")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsClearButton)

        model.clearNearbyPreference()
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.settingsClearButton) == nil)
    }
}
#endif
