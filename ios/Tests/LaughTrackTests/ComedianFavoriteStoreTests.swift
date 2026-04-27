import Foundation
import Testing
@testable import LaughTrackCore

@Suite("ComedianFavoriteStore")
@MainActor
struct ComedianFavoriteStoreTests {
    @Test("resetSavedFavorites clears the per-UUID values dict so prior-session favorites do not leak across sign-outs")
    func resetSavedFavoritesClearsPerUUIDValues() {
        let store = ComedianFavoriteStore()
        store.overwrite(uuid: "comedian-uuid-1", value: true)

        store.resetSavedFavorites()

        #expect(store.value(for: "comedian-uuid-1", fallback: nil) == false)
        #expect(store.value(for: "comedian-uuid-1", fallback: false) == false)
        #expect(store.storedValue(for: "comedian-uuid-1") == nil)
    }
}
