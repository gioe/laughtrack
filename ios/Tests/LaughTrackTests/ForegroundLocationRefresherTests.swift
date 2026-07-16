import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("ForegroundLocationRefresher")
struct ForegroundLocationRefresherTests {
    @Test("geolocated preference + authorized + moved ZIP updates the store and PATCHes the backend")
    @MainActor
    func refreshesWhenEligibleAndZipChanged() async {
        let store = makeStore(name: "moved")
        store.setGeolocatedZip("10012", distanceMiles: 50, city: "New York", state: "NY")
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "90028", city: "Los Angeles", state: "CA")))
        let sync = SpySyncClient()
        let refresher = makeRefresher(store: store, resolver: resolver, authorized: true, sync: sync)

        await refresher.refreshIfEligible()?.value

        #expect(resolver.callCount == 1)
        #expect(store.preference == NearbyPreference(zipCode: "90028", source: .geolocated, distanceMiles: 50, city: "Los Angeles", state: "CA"))
        #expect(sync.calls == [SyncCall(zipCode: "90028", distanceMiles: 50)])
    }

    @Test("unchanged ZIP makes no write and no network call")
    @MainActor
    func stationaryUserIsANoOp() async {
        let store = makeStore(name: "stationary")
        let saved = store.setGeolocatedZip("10012", distanceMiles: 25)
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "10012")))
        let sync = SpySyncClient()
        let refresher = makeRefresher(store: store, resolver: resolver, authorized: true, sync: sync)

        await refresher.refreshIfEligible()?.value

        #expect(resolver.callCount == 1)
        #expect(store.preference == saved)
        #expect(sync.calls.isEmpty)
    }

    @Test("manual preference is never silently overridden by geolocation")
    @MainActor
    func manualPreferenceIsSkipped() async {
        let store = makeStore(name: "manual")
        store.setManualZip("30309", distanceMiles: 25)
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "90028")))
        let sync = SpySyncClient()
        let refresher = makeRefresher(store: store, resolver: resolver, authorized: true, sync: sync)

        let task = refresher.refreshIfEligible()

        #expect(task == nil)
        #expect(resolver.callCount == 0)
        #expect(store.preference == NearbyPreference(zipCode: "30309", source: .manual, distanceMiles: 25))
        #expect(sync.calls.isEmpty)
    }

    @Test("unauthorized location never resolves (no prompt) and never writes")
    @MainActor
    func unauthorizedIsSkipped() async {
        let store = makeStore(name: "unauthorized")
        store.setGeolocatedZip("10012", distanceMiles: 25)
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "90028")))
        let sync = SpySyncClient()
        let refresher = makeRefresher(store: store, resolver: resolver, authorized: false, sync: sync)

        let task = refresher.refreshIfEligible()

        #expect(task == nil)
        #expect(resolver.callCount == 0)
        #expect(sync.calls.isEmpty)
    }

    @Test("no saved preference is a no-op")
    @MainActor
    func emptyPreferenceIsSkipped() async {
        let store = makeStore(name: "empty")
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "90028")))
        let refresher = makeRefresher(store: store, resolver: resolver, authorized: true, sync: SpySyncClient())

        #expect(refresher.refreshIfEligible() == nil)
        #expect(resolver.callCount == 0)
    }

    @Test("nil authorizer (resolver can't report status) is treated as unauthorized")
    @MainActor
    func nilAuthorizerIsSkipped() async {
        let store = makeStore(name: "nil-auth")
        store.setGeolocatedZip("10012", distanceMiles: 25)
        let resolver = StubResolver(result: .success(ResolvedNearbyLocation(zipCode: "90028")))
        let refresher = ForegroundLocationRefresher(
            store: store,
            resolver: resolver,
            authorization: nil,
            syncClient: SpySyncClient()
        )

        #expect(refresher.refreshIfEligible() == nil)
        #expect(resolver.callCount == 0)
    }

    // MARK: - Helpers

    @MainActor
    private func makeRefresher(
        store: NearbyPreferenceStore,
        resolver: StubResolver,
        authorized: Bool,
        sync: SpySyncClient
    ) -> ForegroundLocationRefresher {
        ForegroundLocationRefresher(
            store: store,
            resolver: resolver,
            authorization: StubAuthorizer(isAuthorized: authorized),
            syncClient: sync
        )
    }

    @MainActor
    private func makeStore(name: String) -> NearbyPreferenceStore {
        let suiteName = "ForegroundLocationRefresherTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return NearbyPreferenceStore(appStateStorage: AppStateStorage(userDefaults: defaults))
    }
}

@MainActor
private final class StubResolver: NearbyLocationResolving {
    let result: Result<ResolvedNearbyLocation, Error>
    private(set) var callCount = 0

    init(result: Result<ResolvedNearbyLocation, Error>) {
        self.result = result
    }

    func requestCurrentZip() async throws -> String {
        try await requestCurrentLocation().zipCode
    }

    func requestCurrentLocation() async throws -> ResolvedNearbyLocation {
        callCount += 1
        return try result.get()
    }
}

@MainActor
private final class StubAuthorizer: ForegroundLocationAuthorizing {
    let isLocationAuthorizedForForegroundRefresh: Bool

    init(isAuthorized: Bool) {
        self.isLocationAuthorizedForForegroundRefresh = isAuthorized
    }
}

private struct SyncCall: Equatable {
    let zipCode: String?
    let distanceMiles: Int?
}

private final class SpySyncClient: ProfileLocationPreferenceSyncing, @unchecked Sendable {
    private let lock = NSLock()
    private var _calls: [SyncCall] = []

    var calls: [SyncCall] {
        lock.withLock { _calls }
    }

    func setProfileLocation(zipCode: String?, distanceMiles: Int?) async throws {
        lock.withLock {
            _calls.append(SyncCall(zipCode: zipCode, distanceMiles: distanceMiles))
        }
    }
}
