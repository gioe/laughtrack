import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Club discovery location")
@MainActor
struct ClubsDiscoveryLocationTests {
    @Test("nearby preference seeds ZIP, radius, and location label")
    func nearbyPreferenceSeedsLocation() {
        let preference = NearbyPreference(
            zipCode: "10012",
            source: .manual,
            distanceMiles: 50,
            city: "New York",
            state: "NY"
        )
        let (model, _) = makeModel(preference: preference)

        #expect(model.activeNearbyPreference == preference)
        #expect(model.zipCodeDraft == "10012")
        #expect(model.distance == .regional)
        #expect(model.activeLocationLabel == "New York, NY")
        #expect(model.requestKey.sanitizedZip == "10012")
        #expect(model.requestKey.cacheKey.contains("zip=10012"))
        #expect(model.requestKey.cacheKey.contains("distance=50"))
    }

    @Test("manual location override stays local and default changes do not replace it")
    func manualLocationOverrideStaysLocal() {
        let initial = NearbyPreference(zipCode: "94108", source: .manual, distanceMiles: 25)
        let (model, store) = makeModel(preference: initial)

        model.zipCodeDraft = "30309"
        model.distance = .regional
        #expect(model.applyManualZip())
        model.applyDefaultNearbyPreference(
            NearbyPreference(zipCode: "10801", source: .manual, distanceMiles: 10)
        )

        #expect(model.activeNearbyPreference == NearbyPreference(
            zipCode: "30309",
            source: .manual,
            distanceMiles: 50
        ))
        #expect(model.requestKey.sanitizedZip == "30309")
        #expect(store.preference == initial)
    }

    @Test("invalid ZIP leaves the active location unchanged")
    func invalidZipLeavesLocationUnchanged() {
        let initial = NearbyPreference(zipCode: "94108", source: .manual, distanceMiles: 25)
        let (model, _) = makeModel(preference: initial)

        model.zipCodeDraft = "123"

        #expect(!model.applyManualZip())
        #expect(model.activeNearbyPreference == initial)
        #expect(model.nearbyStatusMessage == "Enter a valid 5-digit ZIP code to search nearby clubs.")
    }

    @Test("club requests and pagination retain ZIP and distance")
    func requestsAndPaginationRetainLocation() async {
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchClubs")
            return clubLocationJSONResponse(#"{"data":[],"total":1,"filters":[]}"#)
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
        let (model, _) = makeModel(
            preference: NearbyPreference(zipCode: "90028", source: .manual, distanceMiles: 100)
        )

        await model.reload(apiClient: client)
        await model.loadMore(apiClient: client)

        #expect(transport.capturedRequests.count == 2)
        for request in transport.capturedRequests {
            #expect(clubLocationQueryValue("zip", from: request.path) == "90028")
            #expect(clubLocationQueryValue("distance", from: request.path) == "100")
        }
        #expect(clubLocationQueryValue("page", from: transport.capturedRequests[0].path) == "0")
        #expect(clubLocationQueryValue("page", from: transport.capturedRequests[1].path) == "1")
    }

    @Test("clearing location uses a nationwide request and a separate cache entry")
    func clearingLocationUsesNationwideCacheEntry() async {
        let transport = StubClientTransport { request, _, _, _ in
            let isNearby = clubLocationQueryValue("zip", from: request.path) != nil
            let id = isNearby ? 101 : 202
            return clubLocationJSONResponse(
                #"{"data":[{"id":\#(id),"name":"Club","imageUrl":""}],"total":1,"filters":[]}"#
            )
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
        let cache = DataCache<LaughTrackCacheKey>()
        let (model, _) = makeModel(
            preference: NearbyPreference(zipCode: "10012", source: .manual, distanceMiles: 25)
        )
        let nearbyCacheKey = model.requestKey.cacheKey

        await model.reload(apiClient: client, cache: cache)
        model.clearLocation()
        let nationwideCacheKey = model.requestKey.cacheKey
        await model.reload(apiClient: client, cache: cache)

        #expect(nearbyCacheKey != nationwideCacheKey)
        #expect(transport.capturedRequests.count == 2)
        #expect(clubLocationQueryValue("zip", from: transport.capturedRequests[1].path) == nil)
        #expect(clubLocationQueryValue("distance", from: transport.capturedRequests[1].path) == nil)
        guard case .success(let page) = model.phase else {
            Issue.record("Expected nationwide club results after clearing location")
            return
        }
        #expect(page.items.map(\.id) == [202])
    }

    @Test("club search view exposes location and radius controls")
    func clubSearchViewExposesLocationControls() throws {
        let source = try String(contentsOf: clubsDiscoverySourceURL(), encoding: .utf8)

        #expect(source.contains("id: \"clubs-distance\""))
        #expect(source.contains("LocationFilterSheet("))
        #expect(source.contains("isZipEditorPresented = true"))
        #expect(source.contains("Set the location used for nearby clubs."))
    }

    private func makeModel(
        preference: NearbyPreference? = nil
    ) -> (ClubsDiscoveryModel, NearbyPreferenceStore) {
        let suiteName = "ClubsDiscoveryLocationTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let store = NearbyPreferenceStore(
            appStateStorage: AppStateStorage(userDefaults: defaults)
        )
        if let preference {
            switch preference.source {
            case .manual:
                store.setManualZip(
                    preference.zipCode,
                    distanceMiles: preference.distanceMiles,
                    city: preference.city,
                    state: preference.state
                )
            case .geolocated:
                store.setGeolocatedZip(
                    preference.zipCode,
                    distanceMiles: preference.distanceMiles,
                    city: preference.city,
                    state: preference.state
                )
            }
        }
        let model = ClubsDiscoveryModel(
            nearbyLocationController: NearbyLocationController(
                store: store,
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            )
        )
        return (model, store)
    }

    private func clubsDiscoverySourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Search/Views/ClubsDiscoveryView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}

private func clubLocationJSONResponse(
    _ body: String,
    status: HTTPResponse.Status = .ok
) -> (HTTPResponse, HTTPBody?) {
    (
        HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
        HTTPBody(body)
    )
}

private func clubLocationQueryValue(_ name: String, from path: String?) -> String? {
    guard let path, let components = URLComponents(string: "https://test.example.com\(path)") else {
        return nil
    }
    return components.queryItems?.first(where: { $0.name == name })?.value
}
