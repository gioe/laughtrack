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

        store.reset()

        let reloaded = PushPermissionStateStore(appStateStorage: storage)
        #expect(reloaded.deferralCount == 0)
        #expect(reloaded.lastDeferredAt == nil)
        #expect(reloaded.postOnboardingFavoriteCount == 0)
    }

    private func makeStorage(name: String) -> AppStateStorage {
        let suiteName = "PushPermissionStateStoreTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return AppStateStorage(userDefaults: defaults)
    }
}
