import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("NearbyPreferenceStore")
struct NearbyPreferenceStoreTests {
    @Test("manual ZIP stores a normalized nearby preference")
    @MainActor
    func setManualZipStoresNormalizedPreference() {
        let store = makeStore(name: "manual")

        let preference = store.setManualZip("10012-1234")

        #expect(preference == NearbyPreference(zipCode: "10012", source: .manual, distanceMiles: 25))
        #expect(store.preference == NearbyPreference(zipCode: "10012", source: .manual, distanceMiles: 25))
    }

    @Test("invalid ZIP input is rejected without replacing the saved preference")
    @MainActor
    func invalidManualZipPreservesExistingPreference() {
        let store = makeStore(name: "invalid")
        store.setGeolocatedZip("30309")

        let preference = store.setManualZip("12")

        #expect(preference == nil)
        #expect(store.preference == NearbyPreference(zipCode: "30309", source: .geolocated, distanceMiles: 25))
    }

    @Test("geolocated ZIP updates the same saved nearby preference")
    @MainActor
    func geolocatedZipReusesStoredPreference() {
        let store = makeStore(name: "shared")
        store.setManualZip("10012")

        store.setGeolocatedZip("60614")

        #expect(store.preference == NearbyPreference(zipCode: "60614", source: .geolocated, distanceMiles: 25))
    }

    @Test("distance updates preserve the saved ZIP and source")
    @MainActor
    func updatingDistancePreservesExistingPreference() {
        let store = makeStore(name: "distance")
        store.setGeolocatedZip("60614")

        store.setDistance(50)

        #expect(store.preference == NearbyPreference(zipCode: "60614", source: .geolocated, distanceMiles: 50))
    }

    @Test("legacy nearby preference payloads default distance to 25 miles")
    func legacyPayloadDefaultsDistance() throws {
        let data = #"{"zipCode":"10012","source":"manual"}"#.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(NearbyPreference.self, from: data)

        #expect(decoded == NearbyPreference(zipCode: "10012", source: .manual, distanceMiles: 25))
    }

    @Test("clearing removes the saved nearby preference")
    @MainActor
    func clearRemovesSavedPreference() {
        let store = makeStore(name: "clear")
        store.setManualZip("10012")

        store.clear()

        #expect(store.preference == nil)
    }

    @MainActor
    private func makeStore(name: String) -> NearbyPreferenceStore {
        let suiteName = "NearbyPreferenceStoreTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults))
    }
}
