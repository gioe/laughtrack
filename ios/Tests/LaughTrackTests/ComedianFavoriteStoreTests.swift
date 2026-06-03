import Combine
import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
@testable import LaughTrackAPIClient
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

    @Test("resetSavedFavorites clears the pending set so prior-session in-flight toggle spinners do not leak across sign-outs")
    func resetSavedFavoritesClearsPending() {
        let store = ComedianFavoriteStore()
        store.pending.insert("comedian-uuid-1")
        #expect(store.isPending("comedian-uuid-1") == true)

        store.resetSavedFavorites()

        #expect(store.isPending("comedian-uuid-1") == false)
    }

    @Test("didAddFavoriteComedian fires exactly once on a successful add-toggle (false → true)")
    func didAddFavoriteComedianFiresOnceOnAdd() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "comedian-fav-add"
        )
        let store = ComedianFavoriteStore()
        let apiClient = makeClient(transport: FavoriteComedianMockTransport(isFavoritedForAdd: true))
        let recorder = SubjectRecorder<String>()
        let cancellable = store.didAddFavoriteComedian.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        let result = await store.toggle(
            uuid: "comedian-uuid-1",
            currentValue: false,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(true) = result else {
            Issue.record("Expected .updated(true), got \(result)")
            return
        }
        #expect(recorder.values == ["comedian-uuid-1"])
    }

    @Test("didAddFavoriteComedian does NOT fire on a remove-toggle (true → false)")
    func didAddFavoriteComedianDoesNotFireOnRemove() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "comedian-fav-remove"
        )
        let store = ComedianFavoriteStore()
        let apiClient = makeClient(transport: FavoriteComedianMockTransport(isFavoritedForRemove: false))
        let recorder = SubjectRecorder<String>()
        let cancellable = store.didAddFavoriteComedian.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        let result = await store.toggle(
            uuid: "comedian-uuid-1",
            currentValue: true,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(false) = result else {
            Issue.record("Expected .updated(false), got \(result)")
            return
        }
        #expect(recorder.values.isEmpty)
    }

    @Test("add → remove → add cycle only emits on the two adds, in order")
    func didAddFavoriteComedianFiresOnEachAddAcrossCycle() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "comedian-fav-cycle"
        )
        let store = ComedianFavoriteStore()
        // FavoriteComedianMockTransport returns isFavorited == operationID == "addFavorite"
        // so a single transport instance handles both legs of each toggle cycle.
        let apiClient = makeClient(transport: FavoriteComedianMockTransport())
        let recorder = SubjectRecorder<String>()
        let cancellable = store.didAddFavoriteComedian.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        _ = await store.toggle(uuid: "comedian-uuid-1", currentValue: false, apiClient: apiClient, authManager: authManager)
        _ = await store.toggle(uuid: "comedian-uuid-1", currentValue: true,  apiClient: apiClient, authManager: authManager)
        _ = await store.toggle(uuid: "comedian-uuid-2", currentValue: false, apiClient: apiClient, authManager: authManager)

        #expect(recorder.values == ["comedian-uuid-1", "comedian-uuid-2"])
    }

    @Test("didAddFavoriteComedian does NOT fire during loadSavedFavorites hydration")
    func didAddFavoriteComedianDoesNotFireOnHydration() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "comedian-fav-hydration"
        )
        let store = ComedianFavoriteStore()
        let apiClient = makeClient(
            transport: FavoriteComedianMockTransport(
                listResponse: .init(
                    data: [
                        .init(
                            id: 101,
                            uuid: "comedian-uuid-1",
                            name: "Taylor Tomlinson",
                            imageUrl: "https://example.com/taylor.png",
                            socialData: .init(id: 101),
                            showCount: 5,
                            isFavorite: true
                        ),
                        .init(
                            id: 102,
                            uuid: "comedian-uuid-2",
                            name: "Atsuko Okatsuka",
                            imageUrl: "https://example.com/atsuko.png",
                            socialData: .init(id: 102),
                            showCount: 7,
                            isFavorite: true
                        ),
                    ]
                )
            )
        )
        let recorder = SubjectRecorder<String>()
        let cancellable = store.didAddFavoriteComedian.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        await store.loadSavedFavorites(apiClient: apiClient, authManager: authManager)

        #expect(store.savedFavoriteComedians.map(\.uuid) == ["comedian-uuid-1", "comedian-uuid-2"])
        #expect(recorder.values.isEmpty)
    }

    private func makeClient(transport: FavoriteComedianMockTransport) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
    }
}

/// Captures every value a Combine subject publishes during a test so emission
/// counts and ordering can be asserted without race conditions. Reads happen on
/// the main actor (the only thread that can drive @MainActor stores), so a
/// plain array is safe.
@MainActor
private final class SubjectRecorder<Value> {
    private(set) var values: [Value] = []

    func append(_ value: Value) {
        values.append(value)
    }
}

/// Mock transport for the three comedian-favorite operations (`getFavorites`,
/// `addFavorite`, `removeFavorite`). Each test instantiates its own transport;
/// behavior is fixed at init time so a test reading captured emissions never
/// races against handler swaps.
private struct FavoriteComedianMockTransport: ClientTransport {
    let listResponse: Components.Schemas.FavoriteListResponse
    let isFavoritedForAdd: Bool
    let isFavoritedForRemove: Bool

    init(
        listResponse: Components.Schemas.FavoriteListResponse = .init(data: []),
        isFavoritedForAdd: Bool = true,
        isFavoritedForRemove: Bool = false
    ) {
        self.listResponse = listResponse
        self.isFavoritedForAdd = isFavoritedForAdd
        self.isFavoritedForRemove = isFavoritedForRemove
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = APIMockEncoder.make()

        switch operationID {
        case "getFavorites":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(listResponse))
            )
        case "addFavorite":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(
                    Components.Schemas.FavoriteResponse(data: .init(isFavorited: isFavoritedForAdd))
                ))
            )
        case "removeFavorite":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(
                    Components.Schemas.FavoriteResponse(data: .init(isFavorited: isFavoritedForRemove))
                ))
            )
        default:
            return (
                HTTPResponse(status: .internalServerError, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"unexpected operation \#(operationID)"}"#)
            )
        }
    }
}
