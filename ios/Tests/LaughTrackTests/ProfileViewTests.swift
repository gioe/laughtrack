#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Profile view", .disabled("TASK-1761: HostedView UI assertions need refresh — see TASK-1740 follow-up"))
@MainActor
struct ProfileViewTests {
    @Test("signed-out profile shows the sign-in CTA and a Settings link")
    func signedOutProfileShowsSignInAndSettingsLink() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile-signed-out")
        let coordinator = NavigationCoordinator<AppRoute>()
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireText("Sign in to LaughTrack")
        try host.requireLabel("Open Settings")
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.settingsScreen) == nil)
    }

    @Test("signed-in profile shows account card with provider name and Sign out")
    func signedInProfileShowsAccountCardAndSignOut() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "shell-profile-signed-in")
        let coordinator = NavigationCoordinator<AppRoute>()
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireLabel("Sign out")
        try host.requireLabel("Open Settings")
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.settingsScreen) == nil)
    }
}
#endif
