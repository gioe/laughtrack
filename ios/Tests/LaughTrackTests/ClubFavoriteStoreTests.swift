import Combine
import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
@testable import LaughTrackAPIClient
@testable import LaughTrackCore

@Suite("ClubFavoriteStore")
@MainActor
struct ClubFavoriteStoreTests {
    @Test("resetSavedFavorites clears the per-clubId values dict so prior-session favorites do not leak across sign-outs")
    func resetSavedFavoritesClearsPerClubValues() {
        let store = ClubFavoriteStore()
        store.overwrite(clubId: 42, value: true)

        store.resetSavedFavorites()

        #expect(store.value(for: 42, fallback: nil) == false)
        #expect(store.value(for: 42, fallback: false) == false)
        #expect(store.storedValue(for: 42) == nil)
    }

    @Test("didAddFavoriteClub fires exactly once on a successful add-toggle (false → true)")
    func didAddFavoriteClubFiresOnceOnAdd() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "club-fav-add"
        )
        let store = ClubFavoriteStore()
        let apiClient = makeClient(transport: FavoriteClubMockTransport(isFavoritedForAdd: true))
        let recorder = SubjectRecorder<Int>()
        let cancellable = store.didAddFavoriteClub.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        let result = await store.toggle(
            clubId: 42,
            currentValue: false,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(true) = result else {
            Issue.record("Expected .updated(true), got \(result)")
            return
        }
        #expect(recorder.values == [42])
    }

    @Test("didAddFavoriteClub does NOT fire on a remove-toggle (true → false)")
    func didAddFavoriteClubDoesNotFireOnRemove() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "club-fav-remove"
        )
        let store = ClubFavoriteStore()
        // The server's response shape on remove is isFavorited=false. Drive the
        // remove path explicitly so a refactor that ever fires on remove (e.g.
        // an accidental if/else swap in toggle) surfaces here.
        let apiClient = makeClient(transport: FavoriteClubMockTransport(isFavoritedForRemove: false))
        let recorder = SubjectRecorder<Int>()
        let cancellable = store.didAddFavoriteClub.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        let result = await store.toggle(
            clubId: 42,
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

    @Test("didAddFavoriteClub does NOT fire during loadSavedFavorites hydration")
    func didAddFavoriteClubDoesNotFireOnHydration() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "club-fav-hydration"
        )
        let store = ClubFavoriteStore()
        let apiClient = makeClient(
            transport: FavoriteClubMockTransport(
                listResponse: .init(
                    data: [
                        .init(id: 42, name: "Cellar", imageUrl: "https://example.com/cellar.png", isFavorite: true),
                        .init(id: 43, name: "Stand", imageUrl: "https://example.com/stand.png", isFavorite: true),
                    ]
                )
            )
        )
        let recorder = SubjectRecorder<Int>()
        let cancellable = store.didAddFavoriteClub.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        await store.loadSavedFavorites(apiClient: apiClient, authManager: authManager)

        #expect(store.savedFavoriteClubs.map(\.id) == [42, 43])
        #expect(recorder.values.isEmpty)
    }

    @Test("add → remove → add cycle only emits on the two adds, in order")
    func didAddFavoriteClubFiresOnEachAddAcrossCycle() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "club-fav-cycle"
        )
        let store = ClubFavoriteStore()
        // FavoriteClubMockTransport returns isFavorited == operationID == "addFavoriteClub"
        // so a single transport instance handles both legs of each toggle cycle.
        let apiClient = makeClient(transport: FavoriteClubMockTransport())
        let recorder = SubjectRecorder<Int>()
        let cancellable = store.didAddFavoriteClub.sink { recorder.append($0) }
        defer { cancellable.cancel() }

        _ = await store.toggle(clubId: 42, currentValue: false, apiClient: apiClient, authManager: authManager)
        _ = await store.toggle(clubId: 42, currentValue: true,  apiClient: apiClient, authManager: authManager)
        _ = await store.toggle(clubId: 43, currentValue: false, apiClient: apiClient, authManager: authManager)

        #expect(recorder.values == [42, 43])
    }

    private func makeClient(transport: FavoriteClubMockTransport) -> Client {
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

/// Mock transport for the three club-favorite operations
/// (`getFavoriteClubs`, `addFavoriteClub`, `removeFavoriteClub`). Each test
/// instantiates its own transport; behavior is fixed at init time so a test
/// reading captured emissions never races against handler swaps.
private struct FavoriteClubMockTransport: ClientTransport {
    let listResponse: Components.Schemas.FavoriteClubListResponse
    /// Value returned in `FavoriteResponse.data.isFavorited` when the test
    /// drives the add path. Defaults to `true` (the production server's
    /// contract on success).
    let isFavoritedForAdd: Bool
    /// Value returned on the remove path. Defaults to `false`.
    let isFavoritedForRemove: Bool

    init(
        listResponse: Components.Schemas.FavoriteClubListResponse = .init(data: []),
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
        case "getFavoriteClubs":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(listResponse))
            )
        case "addFavoriteClub":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(
                    Components.Schemas.FavoriteResponse(data: .init(isFavorited: isFavoritedForAdd))
                ))
            )
        case "removeFavoriteClub":
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
