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
        let controller = makeController(
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
        let controller = makeController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .failure(NearbyLocationError.denied))
        )

        let success = await controller.useCurrentLocation(distanceMiles: 50)

        #expect(!success)
        #expect(controller.statusMessage == NearbyLocationError.denied.recoveryMessage)
        #expect(controller.preference == NearbyPreference(zipCode: "30309", source: .manual, distanceMiles: 25))
    }

    @Test("manual ZIP validation persists immediately and refines city/state from the lookup resolver")
    @MainActor
    func manualZipAndRadiusPersistTogether() async {
        let store = makeStore(name: "manual")
        let zipResolver = MockZipLocationResolver(
            result: .success(ResolvedNearbyLocation(zipCode: "60614", city: "Chicago", state: "IL"))
        )
        let controller = makeController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .success("10012")),
            zipLocationResolver: zipResolver
        )

        let applied = controller.applyManualZip("60614", distanceMiles: 10)
        controller.updateDistanceMiles(100)

        #expect(applied)
        #expect(controller.statusMessage == nil)
        #expect(controller.preference == NearbyPreference(zipCode: "60614", source: .manual, distanceMiles: 100))

        await controller.pendingZipRefinement?.value

        #expect(controller.preference == NearbyPreference(
            zipCode: "60614",
            source: .manual,
            distanceMiles: 100,
            city: "Chicago",
            state: "IL"
        ))
        #expect(store.preference == NearbyPreference(
            zipCode: "60614",
            source: .manual,
            distanceMiles: 100,
            city: "Chicago",
            state: "IL"
        ))
    }

    @Test("manual ZIP refinement does not overwrite the store after the user clears the preference")
    @MainActor
    func manualZipRefinementDroppedAfterClear() async {
        let store = makeStore(name: "manual-cleared")
        let controller = makeController(
            store: store,
            zipLocationResolver: MockZipLocationResolver(
                result: .success(ResolvedNearbyLocation(zipCode: "60614", city: "Chicago", state: "IL"))
            )
        )

        _ = controller.applyManualZip("60614", distanceMiles: 25)
        let inflight = controller.pendingZipRefinement
        controller.clear()
        await inflight?.value

        #expect(controller.preference == nil)
        #expect(store.preference == nil)
    }

    @Test("manual ZIP refinement is silent when the lookup resolver fails")
    @MainActor
    func manualZipRefinementSilentOnLookupFailure() async {
        let store = makeStore(name: "manual-fail")
        let controller = makeController(
            store: store,
            zipLocationResolver: MockZipLocationResolver(result: .failure(ZipLocationLookupError.unknownZip))
        )

        let applied = controller.applyManualZip("99999", distanceMiles: 25)
        await controller.pendingZipRefinement?.value

        #expect(applied)
        #expect(controller.statusMessage == nil)
        #expect(controller.preference == NearbyPreference(zipCode: "99999", source: .manual, distanceMiles: 25))
    }

    @Test("ZIP lookup failures keep discovery available with a clear recovery message")
    @MainActor
    func zipLookupFailureSurfacesMessage() async {
        let store = makeStore(name: "zip-failure")
        let controller = makeController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .failure(NearbyLocationError.zipUnavailable))
        )

        let success = await controller.useCurrentLocation(distanceMiles: 25)

        #expect(!success)
        #expect(controller.statusMessage == NearbyLocationError.zipUnavailable.recoveryMessage)
        #expect(controller.preference == nil)
    }

    @MainActor
    private func makeController(
        store: NearbyPreferenceStore,
        resolver: (any NearbyLocationResolving)? = nil,
        zipLocationResolver: (any ZipLocationResolving)? = nil
    ) -> NearbyLocationController {
        NearbyLocationController(
            store: store,
            resolver: resolver ?? MockNearbyLocationResolver(result: .failure(NearbyLocationError.unavailable)),
            zipLocationResolver: zipLocationResolver ?? MockZipLocationResolver(result: .failure(ZipLocationLookupError.unknownZip))
        )
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

@MainActor
private final class MockZipLocationResolver: ZipLocationResolving {
    let result: Result<ResolvedNearbyLocation, Error>

    init(result: Result<ResolvedNearbyLocation, Error>) {
        self.result = result
    }

    func resolveLocation(forZip zipCode: String) async throws -> ResolvedNearbyLocation {
        try result.get()
    }
}
