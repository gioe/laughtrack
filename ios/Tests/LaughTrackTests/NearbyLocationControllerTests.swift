import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("NearbyLocationController")
struct NearbyLocationControllerTests {
    @Test("current location success stores a geolocated ZIP with the selected distance")
    @MainActor
    func currentLocationSuccessStoresGeolocatedPreference() async {
        let store = makeStore(name: "success")
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .success("10012"))
        )

        let success = await controller.useCurrentLocation(distanceMiles: 50)

        #expect(success)
        #expect(controller.statusMessage == nil)
        #expect(controller.preference == NearbyPreference(zipCode: "10012", source: .geolocated, distanceMiles: 50))
        #expect(store.preference == NearbyPreference(zipCode: "10012", source: .geolocated, distanceMiles: 50))
    }

    @Test("denied location permission surfaces a fallback message without blocking the existing preference")
    @MainActor
    func deniedLocationLeavesSavedPreferenceUntouched() async {
        let store = makeStore(name: "denied")
        store.setManualZip("30309", distanceMiles: 25)
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .failure(NearbyLocationError.denied))
        )

        let success = await controller.useCurrentLocation(distanceMiles: 50)

        #expect(!success)
        #expect(controller.statusMessage == NearbyLocationError.denied.recoveryMessage)
        #expect(controller.preference == NearbyPreference(zipCode: "30309", source: .manual, distanceMiles: 25))
    }

    @Test("manual ZIP validation and distance updates share the same persisted preference")
    @MainActor
    func manualZipAndRadiusPersistTogether() {
        let store = makeStore(name: "manual")
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .success("10012"))
        )

        let applied = controller.applyManualZip("60614", distanceMiles: 10)
        controller.updateDistanceMiles(100)

        #expect(applied)
        #expect(controller.statusMessage == nil)
        #expect(controller.preference == NearbyPreference(zipCode: "60614", source: .manual, distanceMiles: 100))
        #expect(store.preference == NearbyPreference(zipCode: "60614", source: .manual, distanceMiles: 100))
    }

    @Test("ZIP lookup failures keep discovery available with a clear recovery message")
    @MainActor
    func zipLookupFailureSurfacesMessage() async {
        let store = makeStore(name: "zip-failure")
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .failure(NearbyLocationError.zipUnavailable))
        )

        let success = await controller.useCurrentLocation(distanceMiles: 25)

        #expect(!success)
        #expect(controller.statusMessage == NearbyLocationError.zipUnavailable.recoveryMessage)
        #expect(controller.preference == nil)
    }

    @MainActor
    private func makeStore(name: String) -> NearbyPreferenceStore {
        let suiteName = "NearbyLocationControllerTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults))
    }
}

@MainActor
private final class MockNearbyLocationResolver: NearbyLocationResolving {
    let result: Result<String, Error>

    init(result: Result<String, Error>) {
        self.result = result
    }

    func requestCurrentZip() async throws -> String {
        try result.get()
    }
}
