import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackApp
@testable import LaughTrackCore

@Suite("HomeNearbyDiscoveryModel")
struct HomeNearbyDiscoveryModelTests {
    @Test("denied location permission surfaces NearbyLocationError.recoveryMessage via the shared controller")
    @MainActor
    func deniedLocationSurfacesRecoveryMessage() async {
        let store = makeStore(name: "denied")
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .failure(NearbyLocationError.denied))
        )
        let model = HomeNearbyDiscoveryModel(
            nearbyPreferenceStore: store,
            nearbyLocationController: controller,
            appStateStorage: AppStateStorage(userDefaults: makeDefaults(name: "denied-state"))
        )

        await model.useCurrentLocation()

        #expect(model.locationMessage == NearbyLocationError.denied.recoveryMessage)
        #expect(!model.isResolvingLocation)
    }

    @Test("successful location clears any prior status banner on the home model")
    @MainActor
    func successClearsLocationMessage() async {
        let store = makeStore(name: "success")
        let controller = NearbyLocationController(
            store: store,
            resolver: MockNearbyLocationResolver(result: .success("10012"))
        )
        let model = HomeNearbyDiscoveryModel(
            nearbyPreferenceStore: store,
            nearbyLocationController: controller,
            appStateStorage: AppStateStorage(userDefaults: makeDefaults(name: "success-state"))
        )

        await model.useCurrentLocation()

        #expect(model.locationMessage == nil)
        #expect(!model.isResolvingLocation)
    }

    @MainActor
    private func makeStore(name: String) -> NearbyPreferenceStore {
        NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: makeDefaults(name: name)))
    }

    @MainActor
    private func makeDefaults(name: String) -> UserDefaults {
        let suiteName = "HomeNearbyDiscoveryModelTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return defaults
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
