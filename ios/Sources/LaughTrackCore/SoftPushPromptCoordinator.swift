import Combine
import Foundation
import LaughTrackBridge

@MainActor
public final class SoftPushPromptCoordinator: ObservableObject {
    public struct Configuration: Sendable, Equatable {
        public var engagementTrigger: Int
        public var deferralCap: Int

        public init(engagementTrigger: Int = 3, deferralCap: Int = 3) {
            self.engagementTrigger = engagementTrigger
            self.deferralCap = deferralCap
        }

        public static let `default` = Configuration()
    }

    @Published public var isPromptPresented: Bool = false
    @Published public var isDeniedAlertPresented: Bool = false
    @Published public private(set) var hasPresentedThisSession: Bool = false

    public let configuration: Configuration

    private let stateStore: PushPermissionStateStore
    private let notificationPreferenceStore: NotificationPreferenceStore
    private let authorizationStatusProvider: any PushAuthorizationStatusProviding
    private let authorizationRequester: any PushAuthorizationRequesting
    private let systemSettingsOpener: any SystemSettingsOpening
    private let notificationSyncClient: (any NotificationPreferenceSyncing)?
    private let pushTokenManager: (any PushDeviceTokenManaging)?

    public init(
        stateStore: PushPermissionStateStore,
        notificationPreferenceStore: NotificationPreferenceStore,
        authorizationStatusProvider: (any PushAuthorizationStatusProviding)? = nil,
        authorizationRequester: (any PushAuthorizationRequesting)? = nil,
        systemSettingsOpener: (any SystemSettingsOpening)? = nil,
        notificationSyncClient: (any NotificationPreferenceSyncing)? = nil,
        pushTokenManager: (any PushDeviceTokenManaging)? = nil,
        configuration: Configuration = .default
    ) {
        self.stateStore = stateStore
        self.notificationPreferenceStore = notificationPreferenceStore
        self.authorizationStatusProvider = authorizationStatusProvider
            ?? SystemPushAuthorizationStatusProvider()
        self.authorizationRequester = authorizationRequester
            ?? SystemPushAuthorizationRequester()
        self.systemSettingsOpener = systemSettingsOpener ?? SystemSettingsOpener()
        self.notificationSyncClient = notificationSyncClient
        self.pushTokenManager = pushTokenManager
        self.configuration = configuration
    }

    public func handleComedianFavoriteAdded(isPostOnboarding: Bool) async {
        guard isPostOnboarding else { return }
        let count = stateStore.recordPostOnboardingFavorite()
        guard count >= configuration.engagementTrigger else { return }
        guard !stateStore.hasReachedDeferralCap(configuration.deferralCap) else { return }
        guard !notificationPreferenceStore.preferences.favoriteComedianPushAlertsEnabled else { return }
        guard !hasPresentedThisSession else { return }

        let status = await authorizationStatusProvider.currentAuthorizationStatus()
        switch status {
        case .notDetermined:
            hasPresentedThisSession = true
            isPromptPresented = true
        case .authorized:
            // OS allows push but the user has the app's push pref off. Treat as a
            // deliberate Settings choice — don't silently re-enable, don't show
            // the sheet.
            return
        case .denied:
            // Don't burn an engagement moment on the Open-Settings alert
            // without explicit user opt-in; the Settings → Notifications row
            // already exposes that path.
            return
        }
    }

    public func enableTapped() async {
        isPromptPresented = false
        let status = await authorizationStatusProvider.currentAuthorizationStatus()
        switch status {
        case .authorized:
            applyPushPreferenceEnabled()
        case .notDetermined:
            let granted = await authorizationRequester.requestAuthorization()
            if granted {
                applyPushPreferenceEnabled()
            } else {
                // The user tapped Don't Allow on the OS prompt — status now
                // resolves to .denied. Reuse the TASK-2587 Open Settings alert
                // pattern so they understand why nothing happened.
                let postPromptStatus = await authorizationStatusProvider.currentAuthorizationStatus()
                if postPromptStatus == .denied {
                    isDeniedAlertPresented = true
                }
            }
        case .denied:
            isDeniedAlertPresented = true
        }
    }

    public func deferTapped() {
        stateStore.recordDeferral()
        isPromptPresented = false
    }

    public func openSystemSettings() {
        systemSettingsOpener.openAppSystemSettings()
    }

    private func applyPushPreferenceEnabled() {
        notificationPreferenceStore.setFavoriteComedianPushAlertsEnabled(true)
        if let notificationSyncClient {
            Task { [notificationSyncClient] in
                try? await notificationSyncClient.setFavoriteComedianAlertsEnabled(true, channel: .push)
            }
        }
        if let pushTokenManager {
            Task { [pushTokenManager] in
                await pushTokenManager.registerForRemoteNotifications()
            }
        }
    }
}
