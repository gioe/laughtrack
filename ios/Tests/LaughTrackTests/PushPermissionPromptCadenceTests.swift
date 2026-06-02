import Foundation
import Testing
@testable import LaughTrackCore

@Suite("PushPermissionPromptCadence")
struct PushPermissionPromptCadenceTests {
    // MARK: - hasPresentedThisSession filter

    @Test("once the sheet has shown this session, evaluate returns suppressedAlreadyPresentedThisSession regardless of other inputs")
    func suppressesWhenAlreadyPresentedThisSession() {
        // Every other gate is satisfied — engagement met, no deferrals, no backoff.
        // The session flag alone should bind. (Criterion 8456.)
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: 0,
            lastDeferredAt: nil,
            engagementSignalCount: 99,
            sessionCountSinceLastDeferral: 99,
            hasPresentedThisSession: true
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedAlreadyPresentedThisSession)
    }

    // MARK: - maxDeferrals filter (criterion 8457)

    @Test("at maxDeferrals the cadence permanently refuses — Settings is the only enable path")
    func suppressesWhenMaxDeferralsReached() {
        // Even after the longest backoff has elapsed and engagement is huge,
        // hitting maxDeferrals shuts the cadence off for good.
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: PushPermissionPromptCadence.maxDeferrals,
            lastDeferredAt: Self.fixedNow.addingTimeInterval(-365 * Self.day),
            engagementSignalCount: 99,
            sessionCountSinceLastDeferral: 99,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedMaxDeferralsReached)
    }

    @Test("just below maxDeferrals the gate does not bind on the deferral count alone")
    func passesDeferralGateBelowMax() {
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: PushPermissionPromptCadence.maxDeferrals - 1,
            lastDeferredAt: Self.fixedNow.addingTimeInterval(-365 * Self.day),
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .eligible)
    }

    // MARK: - engagement-signal filter

    @Test("below the engagement threshold the cadence suppresses with suppressedInsufficientEngagement")
    func suppressesBelowEngagementThreshold() {
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: 0,
            lastDeferredAt: nil,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals - 1,
            sessionCountSinceLastDeferral: 0,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedInsufficientEngagement)
    }

    @Test("at the engagement threshold with no prior deferral the cadence is eligible")
    func eligibleAtEngagementThresholdWithoutPriorDeferral() {
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: 0,
            lastDeferredAt: nil,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            // Session count is irrelevant before the first deferral — it
            // only gates re-prompts after a decline.
            sessionCountSinceLastDeferral: 0,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .eligible)
    }

    // MARK: - session-count filter (only applies after a deferral)

    @Test("after a deferral, fewer than requiredSessionsSinceDeferral cold launches suppresses with suppressedInsufficientSessionsSinceDeferral")
    func suppressesWhenSessionsSinceDeferralBelowThreshold() {
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow.addingTimeInterval(365 * Self.day), // recency gate would pass
            deferralCount: 1,
            lastDeferredAt: Self.fixedNow,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral - 1,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedInsufficientSessionsSinceDeferral)
    }

    @Test("session-count gate is not enforced before the first deferral")
    func sessionGateNotEnforcedBeforeFirstDeferral() {
        // sessionCountSinceLastDeferral=0 would normally fail the gate, but
        // deferralCount=0 means there's no deferral to count cold-launches
        // against — the gate's contract is post-deferral only.
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: 0,
            lastDeferredAt: nil,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: 0,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .eligible)
    }

    // MARK: - recency/backoff filter (the mocked-TimeProvider filter)

    @Test("3-day backoff applies after the first deferral and blocks re-prompts inside the window")
    func backoffBindsAfterFirstDeferralInsideWindow() {
        let deferralAt = Self.fixedNow
        // 2 days after deferral — inside the 3-day post-1st-decline backoff.
        let now = deferralAt.addingTimeInterval(2 * Self.day)
        let inputs = PushPermissionPromptCadence.Inputs(
            now: now,
            deferralCount: 1,
            lastDeferredAt: deferralAt,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedBackoffActive(daysRemaining: 1))
    }

    @Test("3-day backoff releases on the 3rd day after the first deferral")
    func backoffReleasesAfterThreeDaysFromFirstDeferral() {
        let deferralAt = Self.fixedNow
        let now = deferralAt.addingTimeInterval(3 * Self.day)
        let inputs = PushPermissionPromptCadence.Inputs(
            now: now,
            deferralCount: 1,
            lastDeferredAt: deferralAt,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .eligible)
    }

    @Test("14-day backoff applies after the second deferral and reports daysRemaining")
    func backoffBindsAfterSecondDeferralReportsDaysRemaining() {
        let deferralAt = Self.fixedNow
        let now = deferralAt.addingTimeInterval(5 * Self.day) // inside 14-day window
        let inputs = PushPermissionPromptCadence.Inputs(
            now: now,
            deferralCount: 2,
            lastDeferredAt: deferralAt,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedBackoffActive(daysRemaining: 9))
    }

    @Test("14-day backoff releases on the 14th day after the second deferral")
    func backoffReleasesAfterFourteenDaysFromSecondDeferral() {
        let deferralAt = Self.fixedNow
        let now = deferralAt.addingTimeInterval(14 * Self.day)
        let inputs = PushPermissionPromptCadence.Inputs(
            now: now,
            deferralCount: 2,
            lastDeferredAt: deferralAt,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: false
        )

        #expect(PushPermissionPromptCadence.evaluate(inputs) == .eligible)
    }

    // MARK: - filter precedence

    @Test("hasPresentedThisSession is checked before the deferral cap so its decision wins")
    func sessionFlagPrecedesDeferralCap() {
        let inputs = PushPermissionPromptCadence.Inputs(
            now: Self.fixedNow,
            deferralCount: PushPermissionPromptCadence.maxDeferrals,
            lastDeferredAt: Self.fixedNow,
            engagementSignalCount: PushPermissionPromptCadence.requiredEngagementSignals,
            sessionCountSinceLastDeferral: PushPermissionPromptCadence.requiredSessionsSinceDeferral,
            hasPresentedThisSession: true
        )

        // Both gates would suppress; the session flag is reported first so
        // tests can assert which gate fired without ambiguity.
        #expect(PushPermissionPromptCadence.evaluate(inputs) == .suppressedAlreadyPresentedThisSession)
    }

    // MARK: - Helpers

    private static let day: TimeInterval = 86_400
    /// Arbitrary fixed instant. All time-based tests derive offsets from here
    /// so wall-clock time never enters the assertion — this is the mocked
    /// TimeProvider surface called out in criterion 8458.
    private static let fixedNow = Date(timeIntervalSince1970: 1_700_000_000)
}
