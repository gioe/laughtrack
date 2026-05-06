#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Profile view")
@MainActor
struct ProfileViewTests {
    @Test("signed-out profile shows the sign-in CTA without profile settings")
    func signedOutProfileShowsSignInAndSettingsContent() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-profile-signed-out")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile-signed-out")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: container.resolve(NearbyLocationController.self),
                notificationPreferenceStore: container.resolve(NotificationPreferenceStore.self)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireView(withIdentifier: LaughTrackViewTestID.profileHero)
        try host.requireText("Guest mode")
        try host.requireText("Sign in to sync favorites and recover your account.")
        try host.requireLabel("Continue with Apple")
        try host.requireLabel("Continue with Google")
        #expect(host.findText("Sync favorites across devices") == nil)
        #expect(host.findText("Sign in to LaughTrack") == nil)
        #expect(host.findText("Profile settings") == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.profileSettingsPanel) == nil)
        #expect(host.findText("Favorite comedian alerts") == nil)
        #expect(host.findText("Open Settings") == nil)
    }

    @Test("signed-in profile shows account card with provider name, Sign out, and Delete account")
    func signedInProfileShowsAccountCardAndSignOut() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "shell-profile-signed-in")
        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil,
                zipCode: "94108",
                nearbyDistanceMiles: 25
            )
        }
        await authManager.refreshCurrentUser()
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile-signed-in")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: container.resolve(NearbyLocationController.self),
                notificationPreferenceStore: container.resolve(NotificationPreferenceStore.self)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireView(withIdentifier: LaughTrackViewTestID.profileHero)
        try host.requireText("Ada Lovelace")
        try host.requireLabel("Sign out")
        try host.requireLabel("Delete account")
        try host.requireText("Profile settings")
        try host.requireView(withIdentifier: LaughTrackViewTestID.profileSettingsPanel)
        try host.requireText("Favorite comedian alerts")
        #expect(host.findText("Open Settings") == nil)
    }

    @Test("Delete account action is behind an irreversible confirmation dialog")
    func signedInDeleteAccountRequiresConfirmation() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "shell-profile-delete-confirm")
        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil
            )
        }
        await authManager.refreshCurrentUser()
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-profile-delete-confirm")
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: container.resolve(NearbyLocationController.self),
                notificationPreferenceStore: container.resolve(NotificationPreferenceStore.self)
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        #expect(host.findText("Delete your LaughTrack account?") == nil)

        try host.tapControl(withIdentifier: LaughTrackViewTestID.profileDeleteAccountButton)

        try host.requireText("Delete your LaughTrack account?")
        try host.requireLabel("Delete account permanently")
        try host.requireLabel("Cancel")
    }
}
#endif
