import Combine
import Foundation
import LaughTrackBridge

@MainActor
public final class SoftPushPromptCoordinator: ObservableObject {
    // Single source of truth for which (if any) push-permission UI surface
    // is currently presented. Collapses the previous two independent
    // `@Published` Bools so the view layer transitions through one state
    // at a time and the sheet-dismiss/alert-present race on the same scene
    // can't drop the alert binding.
    public enum Presentation: Equatable {
        case hidden
        case promptingSheet
        case deniedAlert
    }

    @Published public var presentation: Presentation = .hidden
    @Published public private(set) var hasPresentedThisSession: Bool = false

    private let stateStore: PushPermissionStateStore
    private let notificationPreferenceStore: NotificationPreferenceStore
    private let authorizationStatusProvider: any PushAuthorizationStatusProviding
    private let authorizationRequester: any PushAuthorizationRequesting
    private let systemSettingsOpener: any SystemSettingsOpening
    private let notificationSyncClient: (any NotificationPreferenceSyncing)?
    private let pushTokenManager: (any PushDeviceTokenManaging)?
    private let now: () -> Date

    // Tracks whether the user responded via the sheet's Enable / Maybe later
    // buttons. Swipe-to-dismiss bypasses both, so onDismiss treats a
    // false flag as an implicit deferral — otherwise a chronic swiper would
    // be re-prompted every session and the deferralCap would never bind.
    private var hasRespondedExplicitly = false

    // When enableTapped resolves to a denied/declined OS state, presenting
    // the Open-Settings alert while the sheet is still animating out
    // collides on the same scene and SwiftUI silently drops one binding.
    // Buffer the intent here, drive the sheet to .hidden, and let the
    // sheet's onDismiss callback consume the buffer to transition into
    // .deniedAlert — the view layer only ever crosses one boundary per tick.
    private var pendingDeniedAlertAfterDismiss = false

    public init(
        stateStore: PushPermissionStateStore,
        notificationPreferenceStore: NotificationPreferenceStore,
        authorizationStatusProvider: (any PushAuthorizationStatusProviding)? = nil,
        authorizationRequester: (any PushAuthorizationRequesting)? = nil,
        systemSettingsOpener: (any SystemSettingsOpening)? = nil,
        notificationSyncClient: (any NotificationPreferenceSyncing)? = nil,
        pushTokenManager: (any PushDeviceTokenManaging)? = nil,
        now: @escaping () -> Date = { Date() }
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
        self.now = now
    }

    public func handleComedianFavoriteAdded(isPostOnboarding: Bool) async {
        guard isPostOnboarding else { return }
        // Skip the persistent increment only for the permanent-suppression
        // cases — pref already enabled, deferral cap hit, or sheet already
        // shown this session — where no later cadence check could ever
        // flip the prompt back on for this favorite. The cadence's session
        // and backoff gates are deliberately NOT mirrored here: a later
        // cold launch or wall-clock tick can flip them open, and we want
        // the engagement counter to reflect signals accumulated during
        // the suppression window so the prompt fires on the same favorite
        // that clears the gate.
        guard !notificationPreferenceStore.preferences.favoriteComedianPushAlertsEnabled else { return }
        guard !stateStore.hasReachedDeferralCap(PushPermissionPromptCadence.maxDeferrals) else { return }
        guard !hasPresentedThisSession else { return }

        stateStore.recordPostOnboardingFavorite()

        let inputs = PushPermissionPromptCadence.Inputs(
            now: now(),
            deferralCount: stateStore.deferralCount,
            lastDeferredAt: stateStore.lastDeferredAt,
            engagementSignalCount: stateStore.postOnboardingFavoriteCount,
            sessionCountSinceLastDeferral: stateStore.sessionCountSinceLastDeferral,
            hasPresentedThisSession: hasPresentedThisSession
        )
        guard case .eligible = PushPermissionPromptCadence.evaluate(inputs) else { return }

        let status = await authorizationStatusProvider.currentAuthorizationStatus()
        switch status {
        case .notDetermined:
            hasPresentedThisSession = true
            hasRespondedExplicitly = false
            presentation = .promptingSheet
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
        hasRespondedExplicitly = true
        let status = await authorizationStatusProvider.currentAuthorizationStatus()
        switch status {
        case .authorized:
            applyPushPreferenceEnabled()
            presentation = .hidden
        case .notDetermined:
            let granted = await authorizationRequester.requestAuthorization()
            if granted {
                applyPushPreferenceEnabled()
                presentation = .hidden
            } else {
                // requestAuthorization returns false both when the user taps
                // Don't Allow and when the underlying UN call throws (the
                // requester swallows the error to Bool). Surface the same
                // Open Settings alert TASK-2587 ships in Settings either way
                // — silently dropping the error path was a /review-commits
                // finding because it produced no user feedback at all.
                pendingDeniedAlertAfterDismiss = true
                presentation = .hidden
            }
        case .denied:
            pendingDeniedAlertAfterDismiss = true
            presentation = .hidden
        }
    }

    public func deferTapped() {
        hasRespondedExplicitly = true
        stateStore.recordDeferral()
        presentation = .hidden
    }

    public func handleSheetDismissed() {
        // Swipe-to-dismiss never invokes enableTapped/deferTapped, so the
        // explicit-response flag stays false. Count it as an implicit defer
        // so the persistent deferralCap actually binds across sessions.
        if !hasRespondedExplicitly {
            stateStore.recordDeferral()
        }
        hasRespondedExplicitly = false
        if pendingDeniedAlertAfterDismiss {
            pendingDeniedAlertAfterDismiss = false
            presentation = .deniedAlert
        }
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
