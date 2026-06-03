import Combine
import Foundation
import LaughTrackBridge

public struct PushPermissionState: Codable, Equatable, Sendable {
    public var deferralCount: Int
    public var lastDeferredAt: Date?
    public var postOnboardingFavoriteCount: Int
    public var sessionCountSinceLastDeferral: Int

    public init(
        deferralCount: Int = 0,
        lastDeferredAt: Date? = nil,
        postOnboardingFavoriteCount: Int = 0,
        sessionCountSinceLastDeferral: Int = 0
    ) {
        self.deferralCount = deferralCount
        self.lastDeferredAt = lastDeferredAt
        self.postOnboardingFavoriteCount = postOnboardingFavoriteCount
        self.sessionCountSinceLastDeferral = sessionCountSinceLastDeferral
    }

    // Custom decode: tolerate state written by older builds that lacked
    // sessionCountSinceLastDeferral. A missing key decodes as 0, which is the
    // correct semantic — pre-upgrade users have an unknown session-count
    // history, so re-prompting goes through the slowest path (3 cold launches
    // + backoff) before the gate clears.
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.deferralCount = try container.decodeIfPresent(Int.self, forKey: .deferralCount) ?? 0
        self.lastDeferredAt = try container.decodeIfPresent(Date.self, forKey: .lastDeferredAt)
        self.postOnboardingFavoriteCount = try container.decodeIfPresent(
            Int.self, forKey: .postOnboardingFavoriteCount
        ) ?? 0
        self.sessionCountSinceLastDeferral = try container.decodeIfPresent(
            Int.self, forKey: .sessionCountSinceLastDeferral
        ) ?? 0
    }

    private enum CodingKeys: String, CodingKey {
        case deferralCount
        case lastDeferredAt
        case postOnboardingFavoriteCount
        case sessionCountSinceLastDeferral
    }

    public static let `default` = PushPermissionState()
}

@MainActor
public final class PushPermissionStateStore: ObservableObject {
    // Mirrors the FirstEntryAuthChoiceStore.storageKey pattern in
    // ContentView.swift: the UI-test reset path in LaughTrackApp needs to
    // wipe this key, and reaching across a module boundary for a literal
    // would silently desync if the store ever renamed it. `nonisolated`
    // because the class is `@MainActor` but a string constant doesn't need
    // actor isolation and the inner StorageKey enum reads it at file scope.
    public nonisolated static let storageKey = "laughtrack.notifications.softPushPermissionState"

    @Published public private(set) var state: PushPermissionState

    private let appStateStorage: AppStateStorageProtocol
    private let now: () -> Date

    public convenience init() {
        self.init(appStateStorage: AppStateStorage())
    }

    public init(
        appStateStorage: AppStateStorageProtocol,
        now: @escaping () -> Date = { Date() }
    ) {
        self.appStateStorage = appStateStorage
        self.now = now
        self.state = appStateStorage.getValue(
            forKey: StorageKey.state,
            as: PushPermissionState.self
        ) ?? .default
    }

    public var deferralCount: Int { state.deferralCount }
    public var lastDeferredAt: Date? { state.lastDeferredAt }
    public var postOnboardingFavoriteCount: Int { state.postOnboardingFavoriteCount }
    public var sessionCountSinceLastDeferral: Int { state.sessionCountSinceLastDeferral }

    public func recordDeferral() {
        update { state in
            state.deferralCount += 1
            state.lastDeferredAt = self.now()
            // Reset the post-deferral session counter so the cadence's
            // sessionCountSinceLastDeferral gate starts counting from this
            // decline forward.
            state.sessionCountSinceLastDeferral = 0
        }
    }

    /// Increment the post-onboarding engagement counter that feeds
    /// `PushPermissionPromptCadence.Inputs.engagementSignalCount`. Safe to
    /// call from multiple sources (comedian-favorite add, club-favorite add,
    /// show-detail first appearance) — each call is a single +1 against the
    /// same counter; cross-source ordering and de-duplication is the caller's
    /// responsibility (e.g. per-session debouncing of show-detail revisits in
    /// `SoftPushPromptCoordinator`). The underlying storage field is still
    /// named `postOnboardingFavoriteCount` because renaming the Codable key
    /// would invalidate persisted state for users upgrading from TASK-2586.
    @discardableResult
    public func recordEngagementSignal() -> Int {
        update { state in
            state.postOnboardingFavoriteCount += 1
        }
        return state.postOnboardingFavoriteCount
    }

    /// Backward-compat alias for the original TASK-2586 spelling. New
    /// call sites should prefer `recordEngagementSignal` — kept without
    /// deprecation so test fixtures and any external callers keep
    /// compiling cleanly while the rename propagates.
    @discardableResult
    public func recordPostOnboardingFavorite() -> Int {
        recordEngagementSignal()
    }

    /// Increment the post-deferral session counter. Called once per cold
    /// launch from the app entry point. No-op when the user has never
    /// deferred — the cadence only reads sessionCountSinceLastDeferral when
    /// deferralCount > 0, and recordDeferral resets the counter to 0, so
    /// writing on every cold launch before the first deferral churns
    /// AppStateStorage for a value that is never read.
    public func recordColdLaunchSession() {
        guard state.deferralCount > 0 else { return }
        update { state in
            state.sessionCountSinceLastDeferral += 1
        }
    }

    public func hasReachedDeferralCap(_ cap: Int) -> Bool {
        state.deferralCount >= cap
    }

    public func reset() {
        state = .default
        appStateStorage.removeValue(forKey: StorageKey.state)
    }

    private func update(_ mutate: (inout PushPermissionState) -> Void) {
        var next = state
        mutate(&next)
        state = next
        appStateStorage.setValue(next, forKey: StorageKey.state)
    }

    private enum StorageKey {
        static let state = PushPermissionStateStore.storageKey
    }
}
