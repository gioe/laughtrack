#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("Profile settings state")
@MainActor
struct SettingsViewStateTests {
    @Test("Profile location preferences are backed by authenticated user profile state")
    func profileLocationPreferencesReflectAuthenticatedUserState() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "profile-settings")
        let notificationStore = LaughTrackHostedViewTestSupport.makeNotificationPreferenceStore(name: "profile-settings")
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "profile-settings-view")
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
        let favorites = ComedianFavoriteStore()
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: controller,
                notificationPreferenceStore: notificationStore
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        host.scrollDown(pages: 0.8)
        await host.settle()
        try host.requireLabel("Profile location")
        try host.requireLabel("Near Me profile location")
        try host.requireLabel("Near Me is using ZIP 94108 from your profile.")

        controller.applyManualZip("10012", distanceMiles: 50)
        host.render()

        try host.requireLabel("Near Me is using ZIP 10012 from your profile.")
        try host.requireLabel("Clear profile location")

        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil
            )
        }
        await authManager.refreshCurrentUser()
        await host.settle()

        try host.requireLabel("No profile location is saved. Enter a ZIP or use current location to power Near Me.")
        #expect(host.findText("Clear profile location") == nil)
    }

    @Test("Profile notification preferences are backed by authenticated user state")
    func profileNotificationPreferencesReflectAuthenticatedUserState() async throws {
        let nearbyStore = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "profile-notifications")
        let suiteName = "SettingsViewStateTests.notifications.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let notificationStorage = AppStateStorage(userDefaults: defaults)
        let notificationStore = NotificationPreferenceStore(appStateStorage: notificationStorage)
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: nearbyStore)
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "profile-notifications-view")
        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil,
                emailShowNotifications: true,
                pushShowNotifications: true
            )
        }
        await authManager.refreshCurrentUser()
        let favorites = ComedianFavoriteStore()
        let host = HostedView(
            ProfileView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyLocationController: controller,
                notificationPreferenceStore: notificationStore
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(NavigationCoordinator<AppRoute>())
            .environmentObject(favorites)
            .environmentObject(authManager)
            .environmentObject(LoginModalPresenter())
        )

        host.scrollDown(pages: 1.2)
        await host.settle()
        try host.requireLabel("Favorite comedian alerts")
        try host.requireLabel("Email, New-show alerts sent to ada@example.com.")
        try host.requireLabel("Push notifications, New-show alerts delivered on this device.")
        #expect(notificationStore.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(notificationStore.preferences.favoriteComedianPushAlertsEnabled)

        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil,
                emailShowNotifications: false,
                pushShowNotifications: false
            )
        }
        await authManager.refreshCurrentUser()
        await host.settle()
        #expect(!notificationStore.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(!notificationStore.preferences.favoriteComedianPushAlertsEnabled)
    }
}
#endif
