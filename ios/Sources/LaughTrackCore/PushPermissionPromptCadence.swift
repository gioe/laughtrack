import Foundation

/// Pure value type that decides whether the soft push-permission prompt should
/// surface at a given moment. All side-effecting concerns (OS authorization
/// queries, persistence, UI state) live in `SoftPushPromptCoordinator`; this
/// type only evaluates the multi-signal gating filters over a snapshot of
/// inputs.
public struct PushPermissionPromptCadence: Sendable, Equatable {
    /// Snapshot of the state the cadence evaluates. Tests construct this
    /// directly with a fixed `now` to mock the clock without touching the
    /// store or wall-clock time — that is the "mocked TimeProvider" surface.
    public struct Inputs: Sendable, Equatable {
        public var now: Date
        public var deferralCount: Int
        public var lastDeferredAt: Date?
        public var engagementSignalCount: Int
        public var sessionCountSinceLastDeferral: Int
        public var hasPresentedThisSession: Bool

        public init(
            now: Date,
            deferralCount: Int,
            lastDeferredAt: Date?,
            engagementSignalCount: Int,
            sessionCountSinceLastDeferral: Int,
            hasPresentedThisSession: Bool
        ) {
            self.now = now
            self.deferralCount = deferralCount
            self.lastDeferredAt = lastDeferredAt
            self.engagementSignalCount = engagementSignalCount
            self.sessionCountSinceLastDeferral = sessionCountSinceLastDeferral
            self.hasPresentedThisSession = hasPresentedThisSession
        }
    }

    /// Outcome of the gating evaluation. The suppression cases name the
    /// specific filter that rejected the inputs so callers (and tests) can
    /// reason about which gate bound.
    public enum Decision: Sendable, Equatable {
        case eligible
        case suppressedAlreadyPresentedThisSession
        case suppressedMaxDeferralsReached
        case suppressedInsufficientEngagement
        case suppressedInsufficientSessionsSinceDeferral
        case suppressedBackoffActive(daysRemaining: Int)
    }

    /// After this many declines the soft prompt never reappears — Settings
    /// becomes the only enable path. (Criterion 8457.)
    public static let maxDeferrals = 3

    /// Minimum qualifying engagement signals (currently post-onboarding
    /// favorites) before the prompt is even considered.
    public static let requiredEngagementSignals = 3

    /// Minimum cold-launch sessions that must elapse after a deferral before
    /// the prompt is eligible again. Avoids re-prompting on the same launch
    /// the user just declined on, even if engagement keeps climbing.
    public static let requiredSessionsSinceDeferral = 3

    /// Growing time-based backoff indexed by `deferralCount`. Index 0 (no
    /// prior deferral) carries no backoff. Subsequent indices stretch the
    /// minimum wait so the prompt becomes progressively less intrusive.
    public static let backoffDays: [Int] = [0, 3, 14]

    /// Evaluate the cadence over a snapshot. Each filter rejects independently
    /// so callers and tests can pin the responsible gate.
    public static func evaluate(_ inputs: Inputs) -> Decision {
        if inputs.hasPresentedThisSession {
            return .suppressedAlreadyPresentedThisSession
        }
        if inputs.deferralCount >= maxDeferrals {
            return .suppressedMaxDeferralsReached
        }
        if inputs.engagementSignalCount < requiredEngagementSignals {
            return .suppressedInsufficientEngagement
        }
        if inputs.deferralCount > 0 {
            if inputs.sessionCountSinceLastDeferral < requiredSessionsSinceDeferral {
                return .suppressedInsufficientSessionsSinceDeferral
            }
            let backoffIndex = min(inputs.deferralCount, backoffDays.count - 1)
            let minDays = backoffDays[backoffIndex]
            if minDays > 0, let lastDeferred = inputs.lastDeferredAt {
                let elapsedSeconds = inputs.now.timeIntervalSince(lastDeferred)
                let elapsedDays = Int(elapsedSeconds / 86_400)
                if elapsedDays < minDays {
                    return .suppressedBackoffActive(daysRemaining: minDays - elapsedDays)
                }
            }
        }
        return .eligible
    }
}
