import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("Profile settings state")
@MainActor
struct SettingsViewStateTests {
    @Test("Profile location preferences are backed by authenticated user profile state")
    func profileLocationPreferencesReflectAuthenticatedUserState() async throws {
        let store = LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "profile-settings")
        let controller = LaughTrackHostedViewTestSupport.makeNearbyLocationController(store: store)
        let settingsModel = SettingsNearbyPreferenceModel(nearbyLocationController: controller)
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
        let profileUser = try #require(authManager.currentUser)
        settingsModel.replaceServerBackedPreference(from: profileUser)

        #expect(settingsModel.nearbyPreference?.zipCode == "94108")
        #expect(settingsModel.nearbyPreference?.distanceMiles == 25)
        #expect(settingsModel.zipCodeDraft == "94108")
        #expect(settingsModel.distanceMiles == 25)

        controller.applyManualZip("10012", distanceMiles: 50)

        #expect(settingsModel.nearbyPreference?.zipCode == "10012")
        #expect(settingsModel.nearbyPreference?.distanceMiles == 50)
        #expect(settingsModel.zipCodeDraft == "10012")
        #expect(settingsModel.distanceMiles == 50)

        authManager.loadUserRequest = {
            AuthenticatedUser(
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil
            )
        }
        await authManager.refreshCurrentUser()
        let profileUserWithoutLocation = try #require(authManager.currentUser)
        settingsModel.replaceServerBackedPreference(from: profileUserWithoutLocation)

        #expect(settingsModel.nearbyPreference == nil)
        #expect(settingsModel.zipCodeDraft == "")
        #expect(settingsModel.distanceMiles == NearbyPreference.defaultDistanceMiles)
    }

    @Test("Profile notification preferences are backed by authenticated user state")
    func profileNotificationPreferencesReflectAuthenticatedUserState() async throws {
        let suiteName = "SettingsViewStateTests.notifications.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let notificationStorage = AppStateStorage(userDefaults: defaults)
        let notificationStore = NotificationPreferenceStore(appStateStorage: notificationStorage)
        let notificationModel = SettingsNotificationPreferenceModel(store: notificationStore)
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
        let profileUser = try #require(authManager.currentUser)
        notificationModel.replaceServerBackedPreferences(from: profileUser)

        #expect(notificationModel.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(notificationModel.preferences.favoriteComedianPushAlertsEnabled)
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
        let updatedProfileUser = try #require(authManager.currentUser)
        notificationModel.replaceServerBackedPreferences(from: updatedProfileUser)

        #expect(!notificationModel.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(!notificationModel.preferences.favoriteComedianPushAlertsEnabled)
        #expect(!notificationStore.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(!notificationStore.preferences.favoriteComedianPushAlertsEnabled)
    }
}
