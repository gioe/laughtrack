import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("PushPermissionStateStore")
@MainActor
struct PushPermissionStateStoreTests {
    @Test("recordDeferral increments count and stamps lastDeferredAt from the injected clock")
    func recordDeferralIncrementsCountAndStampsTimestamp() {
        let storage = makeStorage(name: "defer")
        let fixedDate = Date(timeIntervalSince1970: 1_000_000)
        let store = PushPermissionStateStore(appStateStorage: storage) { fixedDate }

        store.recordDeferral()

        #expect(store.deferralCount == 1)
        #expect(store.lastDeferredAt == fixedDate)
    }

    @Test("recordDeferral compounds across multiple calls")
    func recordDeferralCompoundsAcrossCalls() {
        let storage = makeStorage(name: "defer-twice")
        let store = PushPermissionStateStore(appStateStorage: storage)

        store.recordDeferral()
        store.recordDeferral()
        store.recordDeferral()

        #expect(store.deferralCount == 3)
        #expect(store.lastDeferredAt != nil)
    }

    @Test("recordPostOnboardingFavorite returns the cumulative running count")
    func recordPostOnboardingFavoriteReturnsRunningCount() {
        let storage = makeStorage(name: "favorites")
        let store = PushPermissionStateStore(appStateStorage: storage)

        #expect(store.recordPostOnboardingFavorite() == 1)
        #expect(store.recordPostOnboardingFavorite() == 2)
        #expect(store.recordPostOnboardingFavorite() == 3)
        #expect(store.postOnboardingFavoriteCount == 3)
    }

    @Test("recordEngagementSignal increments the same counter as recordPostOnboardingFavorite")
    func recordEngagementSignalIncrementsSharedCounter() {
        let storage = makeStorage(name: "engagement-signals")
        let store = PushPermissionStateStore(appStateStorage: storage)

        // Mixing the two spellings against the same store must yield a
        // single monotonically-increasing count — the new wiring from
        // ShowDetailView and ClubFavoriteStore (TASK-2606) shares the
        // counter with the existing ComedianFavoriteStore (TASK-2586)
        // call site, so a regression that split them into separate
        // counters would silently halve the cadence's signal count.
        #expect(store.recordEngagementSignal() == 1)
        #expect(store.recordPostOnboardingFavorite() == 2)
        #expect(store.recordEngagementSignal() == 3)
        #expect(store.postOnboardingFavoriteCount == 3)
    }

    @Test("state persists across store instances when backed by the same storage")
    func statePersistsAcrossStoreInstances() {
        let storage = makeStorage(name: "persist")
        let fixedDate = Date(timeIntervalSince1970: 2_000_000)
        let first = PushPermissionStateStore(appStateStorage: storage) { fixedDate }
        first.recordDeferral()
        first.recordPostOnboardingFavorite()
        first.recordPostOnboardingFavorite()

        let reloaded = PushPermissionStateStore(appStateStorage: storage)

        #expect(reloaded.deferralCount == 1)
        #expect(reloaded.lastDeferredAt == fixedDate)
        #expect(reloaded.postOnboardingFavoriteCount == 2)
    }

    @Test("hasReachedDeferralCap reports threshold crossing")
    func hasReachedDeferralCapReportsThresholdCrossing() {
        let store = PushPermissionStateStore(appStateStorage: makeStorage(name: "cap"))
        #expect(!store.hasReachedDeferralCap(3))

        store.recordDeferral()
        store.recordDeferral()
        #expect(!store.hasReachedDeferralCap(3))

        store.recordDeferral()
        #expect(store.hasReachedDeferralCap(3))
    }

    @Test("reset clears persisted soft-prompt state")
    func resetClearsPersistedState() {
        let storage = makeStorage(name: "reset")
        let store = PushPermissionStateStore(appStateStorage: storage)
        store.recordDeferral()
        store.recordPostOnboardingFavorite()
        store.recordColdLaunchSession()

        store.reset()

        let reloaded = PushPermissionStateStore(appStateStorage: storage)
        #expect(reloaded.deferralCount == 0)
        #expect(reloaded.lastDeferredAt == nil)
        #expect(reloaded.postOnboardingFavoriteCount == 0)
        #expect(reloaded.sessionCountSinceLastDeferral == 0)
    }

    @Test("recordColdLaunchSession increments the post-deferral session counter once a deferral has been recorded")
    func recordColdLaunchSessionIncrementsCounter() {
        let store = PushPermissionStateStore(appStateStorage: makeStorage(name: "session-incr"))
        store.recordDeferral()

        store.recordColdLaunchSession()
        store.recordColdLaunchSession()
        store.recordColdLaunchSession()

        #expect(store.sessionCountSinceLastDeferral == 3)
    }

    @Test("recordColdLaunchSession is a no-op before any deferral — avoids churning AppStateStorage for a value the cadence never reads")
    func recordColdLaunchSessionNoOpBeforeFirstDeferral() {
        let store = PushPermissionStateStore(appStateStorage: makeStorage(name: "session-noop"))

        store.recordColdLaunchSession()
        store.recordColdLaunchSession()

        #expect(store.sessionCountSinceLastDeferral == 0)
    }

    @Test("recordDeferral resets the post-deferral session counter so the cadence's session gate restarts")
    func recordDeferralResetsSessionCounter() {
        let store = PushPermissionStateStore(appStateStorage: makeStorage(name: "session-reset"))
        store.recordDeferral()
        store.recordColdLaunchSession()
        store.recordColdLaunchSession()
        #expect(store.sessionCountSinceLastDeferral == 2)

        store.recordDeferral()

        #expect(store.sessionCountSinceLastDeferral == 0)
        #expect(store.deferralCount == 2)
    }

    @Test("sessionCountSinceLastDeferral persists across store instances")
    func sessionCounterPersistsAcrossInstances() {
        let storage = makeStorage(name: "session-persist")
        let first = PushPermissionStateStore(appStateStorage: storage)
        first.recordDeferral()
        first.recordColdLaunchSession()
        first.recordColdLaunchSession()

        let reloaded = PushPermissionStateStore(appStateStorage: storage)

        #expect(reloaded.sessionCountSinceLastDeferral == 2)
    }

    @Test("decode of legacy state JSON that lacks sessionCountSinceLastDeferral defaults to 0")
    func decodeLegacyStateMissingSessionCountDefaultsToZero() throws {
        // The state field was added in this task; persisted state from
        // earlier builds lacks the key. decodeIfPresent must default to 0
        // so an upgrade doesn't crash on first launch.
        let legacyJSON = """
        {
            "deferralCount": 1,
            "postOnboardingFavoriteCount": 5
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(PushPermissionState.self, from: legacyJSON)

        #expect(decoded.deferralCount == 1)
        #expect(decoded.postOnboardingFavoriteCount == 5)
        #expect(decoded.sessionCountSinceLastDeferral == 0)
    }

    private func makeStorage(name: String) -> AppStateStorage {
        let suiteName = "PushPermissionStateStoreTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return AppStateStorage(userDefaults: defaults)
    }
}
