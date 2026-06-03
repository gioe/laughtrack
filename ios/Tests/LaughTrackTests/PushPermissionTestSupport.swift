import Foundation
import LaughTrackBridge
import LaughTrackCore

// Shared fixtures for the push-permission test suites
// (SoftPushPromptCoordinatorTests, NotificationPreferenceStoreTests,
// OnboardingTests). Before this file existed, each suite declared its own
// near-identical Mock/Scripted/Sequenced/Recording variants — diverging only
// on type names — and a TASK-2598 reviewer flagged the pattern as a recipe
// for the next contributor to add yet another copy. Extend this file when
// future push-funnel tests need a new fixture rather than re-declaring one
// at file scope.

/// `PushAuthorizationStatusProviding` fixture that always returns the same
/// status. Replaces the file-local `MockPushAuthorizationStatusProvider`
/// (NotificationPreferenceStoreTests) and
/// `OnboardingMockPushAuthorizationStatusProvider` (OnboardingTests).
struct SingleStatusPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
    let status: PushAuthorizationStatus

    func currentAuthorizationStatus() async -> PushAuthorizationStatus {
        status
    }
}

/// `PushAuthorizationStatusProviding` fixture that walks through a scripted
/// sequence of statuses, repeating the last entry forever once exhausted.
/// Replaces `ScriptedPushAuthorizationStatusProvider`
/// (SoftPushPromptCoordinatorTests) and the previously-duplicated
/// `SequencedPushAuthorizationStatusProvider`
/// (NotificationPreferenceStoreTests).
actor SequencedPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
    private var sequence: [PushAuthorizationStatus]
    private let fallback: PushAuthorizationStatus

    init(sequence: [PushAuthorizationStatus]) {
        precondition(!sequence.isEmpty)
        self.sequence = sequence
        self.fallback = sequence.last!
    }

    func currentAuthorizationStatus() async -> PushAuthorizationStatus {
        if sequence.count > 1 {
            return sequence.removeFirst()
        }
        return sequence.first ?? fallback
    }
}

/// `PushAuthorizationRequesting` fixture that returns a fixed result and
/// counts how many times `requestAuthorization()` was invoked. Replaces the
/// three file-local copies previously named
/// `RecordingPushAuthorizationRequester` (SoftPush + NotificationPreference)
/// and `RecordingPushPermissionRequester` (Onboarding).
actor RecordingPushAuthorizationRequester: PushAuthorizationRequesting {
    private let result: Bool
    private(set) var requestCount = 0

    init(result: Bool) {
        self.result = result
    }

    func requestAuthorization() async -> Bool {
        requestCount += 1
        return result
    }
}

/// In-memory `AnalyticsManagerProtocol` stub used by every push-funnel
/// test suite. Moved here from SoftPushPromptCoordinatorTests so the
/// recorder's structural home is next to the other push-permission fixtures
/// its callers already reach for. Named `RecordingPushAnalyticsManager`
/// (not just `RecordingAnalyticsManager`) to avoid colliding with the
/// distinct file-private `RecordingAnalyticsManager` in
/// `AppBootstrapAnalyticsLifecycleTests.swift`, which records different
/// fields for sign-in/sign-out lifecycle assertions.
@MainActor
final class RecordingPushAnalyticsManager: AnalyticsManagerProtocol {
    struct Recorded {
        let name: String
        let parameters: [String: Any]?

        func string(_ key: String) -> String? { parameters?[key] as? String }
        func bool(_ key: String) -> Bool? { parameters?[key] as? Bool }
        func int(_ key: String) -> Int? { parameters?[key] as? Int }
    }

    private(set) var events: [Recorded] = []

    func addProvider(_ provider: AnalyticsProvider) {}

    func track(_ event: AnalyticsEvent) {
        events.append(Recorded(name: event.name, parameters: event.parameters))
    }

    func track(_ name: String, parameters: [String: Any]?) {
        events.append(Recorded(name: name, parameters: parameters))
    }

    func trackScreen(_ name: String, parameters: [String: Any]?) {}
    func setUserProperty(_ value: String?, forName name: String) {}
    func setUserID(_ userID: String?) {}
    func reset() {}
}
