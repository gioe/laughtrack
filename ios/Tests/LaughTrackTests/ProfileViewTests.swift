#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Profile view")
@MainActor
struct ProfileViewTests {
    @Test("signed-out profile shows the sign-in CTA and a Settings link")
    func signedOutProfileShowsSignInAndSettingsContent() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile-signed-out")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile-signed-out")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: container.resolve(NearbyLocationController.self)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        #expect(host.findText("Sign in to LaughTrack") == nil)
        try host.requireText("Browse defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)
        #expect(host.findText("Open Settings") == nil)
    }

    @Test("signed-in profile shows account card with provider name and Sign out")
    func signedInProfileShowsAccountCardAndSignOut() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "shell-profile-signed-in")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile-signed-in")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: container.resolve(NearbyLocationController.self)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireLabel("Sign out")
        try host.requireText("Browse defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsNearbyEmptyState)
        #expect(host.findText("Open Settings") == nil)
    }
}
#endif
