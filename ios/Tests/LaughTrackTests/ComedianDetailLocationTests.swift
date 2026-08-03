import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Comedian detail location")
@MainActor
struct ComedianDetailLocationTests {
    @Test("comedian detail starts nationwide and resets pagination when location changes")
    func comedianDetailLocationLifecycle() async throws {
        let suiteName = "ComedianDetailLocationTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let store = NearbyPreferenceStore(
            appStateStorage: AppStateStorage(userDefaults: defaults)
        )
        let savedPreference = try #require(
            store.setManualZip("94108", distanceMiles: 25)
        )
        let model = ShowsListModel(
            nearbyLocationController: NearbyLocationController(
                store: store,
                resolver: StubNearbyLocationResolver(),
                zipLocationResolver: StubZipLocationResolver()
            ),
            pinnedComedianName: "Mark Normand",
            initialUseDateRange: false,
            startsWithNearbyLocation: false,
            pageSize: 5
        )
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == "searchShows")
            return comedianLocationJSONResponse(
                #"{"data":[],"total":10,"filters":[],"zipCapTriggered":false}"#
            )
        }
        let client = Client(
            serverURL: URL(string: "https://test.example.com")!,
            configuration: .laughTrack,
            transport: transport
        )

        let nationwideRequest = model.requestKey
        await model.reload(apiClient: client)
        await model.loadPage(1, apiClient: client)

        #expect(model.activeNearbyPreference == nil)
        #expect(comedianLocationQueryValue("comedian", from: transport.capturedRequests[0].path) == "Mark Normand")
        #expect(comedianLocationQueryValue("zip", from: transport.capturedRequests[0].path) == nil)
        #expect(comedianLocationQueryValue("distance", from: transport.capturedRequests[0].path) == nil)
        #expect(comedianLocationQueryValue("page", from: transport.capturedRequests[1].path) == "1")

        model.distance = .regional
        #expect(model.requestKey == nationwideRequest)
        model.zipCodeDraft = "10012"
        #expect(model.applyManualZip())
        let nearbyRequest = model.requestKey
        #expect(nearbyRequest != nationwideRequest)

        await model.reload(apiClient: client)
        guard case .success(let nearbyPage) = model.phase else {
            Issue.record("Expected nearby reload to succeed")
            return
        }
        #expect(nearbyPage.page == 0)
        #expect(comedianLocationQueryValue("zip", from: transport.capturedRequests[2].path) == "10012")
        #expect(comedianLocationQueryValue("distance", from: transport.capturedRequests[2].path) == "50")
        #expect(comedianLocationQueryValue("page", from: transport.capturedRequests[2].path) == "0")

        await model.loadPage(1, apiClient: client)
        #expect(comedianLocationQueryValue("zip", from: transport.capturedRequests[3].path) == "10012")
        #expect(comedianLocationQueryValue("distance", from: transport.capturedRequests[3].path) == "50")
        #expect(comedianLocationQueryValue("page", from: transport.capturedRequests[3].path) == "1")

        model.clearLocation()
        #expect(model.requestKey == nationwideRequest)
        await model.reload(apiClient: client)

        guard case .success(let clearedPage) = model.phase else {
            Issue.record("Expected nationwide reload after clearing location")
            return
        }
        #expect(clearedPage.page == 0)
        #expect(comedianLocationQueryValue("zip", from: transport.capturedRequests[4].path) == nil)
        #expect(comedianLocationQueryValue("distance", from: transport.capturedRequests[4].path) == nil)
        #expect(comedianLocationQueryValue("page", from: transport.capturedRequests[4].path) == "0")
        #expect(store.preference == savedPreference)
    }

    @Test("comedian detail opts into nationwide pinned shows without changing club detail")
    func comedianDetailUsesNationwidePinnedShowsPolicy() throws {
        let comedianSource = try String(
            contentsOf: appSourceURL(relativePath: "Detail/Views/ComedianDetailView.swift"),
            encoding: .utf8
        )
        let clubSource = try String(
            contentsOf: appSourceURL(relativePath: "Detail/Views/ClubDetailView.swift"),
            encoding: .utf8
        )
        let pinnedSource = try String(
            contentsOf: appSourceURL(relativePath: "Components/PinnedShowsList.swift"),
            encoding: .utf8
        )

        #expect(comedianSource.contains("startsNationwide: true"))
        #expect(!clubSource.contains("startsNationwide:"))
        #expect(pinnedSource.contains("startsWithNearbyLocation: !startsNationwide"))
        #expect(pinnedSource.contains("ShowsListView(apiClient: apiClient, model: model, compactMode: true)"))
    }

    private func appSourceURL(relativePath: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp")
            .appendingPathComponent(relativePath)
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}

private func comedianLocationJSONResponse(
    _ body: String,
    status: HTTPResponse.Status = .ok
) -> (HTTPResponse, HTTPBody?) {
    (
        HTTPResponse(status: status, headerFields: [.contentType: "application/json"]),
        HTTPBody(body)
    )
}

private func comedianLocationQueryValue(_ name: String, from path: String?) -> String? {
    guard let path, let components = URLComponents(string: "https://test.example.com\(path)") else {
        return nil
    }
    return components.queryItems?.first(where: { $0.name == name })?.value
}
