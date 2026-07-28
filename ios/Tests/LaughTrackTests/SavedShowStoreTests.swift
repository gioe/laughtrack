import Combine
import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("SavedShowStore")
@MainActor
struct SavedShowStoreTests {
    @Test("loads per-show state and independent paginated upcoming and past collections")
    func loadsStateAndCollections() async throws {
        let auth = await makeAuth(accountId: "account-a")
        let transport = StubClientTransport { request, _, _, operationID in
            let encoder = APIMockEncoder.make()
            switch operationID {
            case Operations.GetSavedShowState.id:
                return jsonResponse(
                    .ok,
                    Components.Schemas.SavedShowStateResponse(
                        data: .init(isSaved: true)
                    ),
                    encoder: encoder
                )
            case Operations.GetSavedShows.id:
                let period = queryValue("period", from: request.path)
                let page = Int(queryValue("page", from: request.path) ?? "") ?? 1
                let shows = period == "past"
                    ? [makeShow(id: 8, date: Date(timeIntervalSince1970: 100))]
                    : [
                        makeShow(id: 11, date: Date(timeIntervalSince1970: 300)),
                        makeShow(id: 12, date: Date(timeIntervalSince1970: 400)),
                    ]
                return jsonResponse(
                    .ok,
                    Components.Schemas.SavedShowListResponse(
                        data: shows,
                        total: period == "past" ? 21 : 42,
                        page: page,
                        size: 20,
                        totalPages: period == "past" ? 2 : 3
                    ),
                    encoder: encoder
                )
            default:
                throw URLError(.badServerResponse)
            }
        }
        let client = makeClient(transport: transport)
        let harness = makeHarness()

        await harness.store.loadState(
            showId: 11,
            apiClient: client,
            authManager: auth
        )
        await harness.store.loadSavedShows(
            period: .upcoming,
            page: 2,
            apiClient: client,
            authManager: auth
        )
        await harness.store.loadSavedShows(
            period: .past,
            page: 1,
            apiClient: client,
            authManager: auth
        )

        #expect(harness.store.value(for: 11) == true)
        #expect(harness.store.upcomingPage?.shows.map(\.id) == [11, 12])
        #expect(harness.store.upcomingPage?.page == 2)
        #expect(harness.store.upcomingPage?.total == 42)
        #expect(harness.store.pastPage?.shows.map(\.id) == [8])
        #expect(harness.store.pastPage?.totalPages == 2)
        #expect(harness.store.upcomingPhase == .loaded)
        #expect(harness.store.pastPhase == .loaded)

        let listPaths = transport.capturedRequests
            .filter { $0.operationID == Operations.GetSavedShows.id }
            .compactMap(\.path)
        #expect(listPaths.contains { $0.contains("period=upcoming") && $0.contains("page=2") })
        #expect(listPaths.contains { $0.contains("period=past") && $0.contains("page=1") })
    }

    @Test("memory and persistent collection caches remain scoped to the active account")
    func cachesAreAccountScoped() async {
        let harness = makeHarness()
        let authA = await makeAuth(accountId: "account-a")
        let authB = await makeAuth(accountId: "account-b")
        let transport = StubClientTransport { request, _, _, _ in
            let accountShow = request.path?.contains("page=2") == true ? 202 : 101
            return jsonResponse(
                .ok,
                Components.Schemas.SavedShowListResponse(
                    data: [makeShow(id: accountShow)],
                    total: 1,
                    page: accountShow == 202 ? 2 : 1,
                    size: 20,
                    totalPages: accountShow == 202 ? 2 : 1
                ),
                encoder: APIMockEncoder.make()
            )
        }
        let client = makeClient(transport: transport)

        await harness.store.loadSavedShows(
            period: .upcoming,
            apiClient: client,
            authManager: authA
        )
        await harness.store.loadSavedShows(
            period: .upcoming,
            page: 2,
            apiClient: client,
            authManager: authB
        )

        #expect(harness.store.upcomingPage?.shows.map(\.id) == [202])
        #expect(transport.capturedRequests.count == 2)
    }

    @Test("save is optimistic while the request is in flight")
    func saveIsOptimistic() async {
        let auth = await makeAuth(accountId: "account-a")
        let gate = SuspensionGate()
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == Operations.SaveShow.id)
            await gate.suspend()
            return jsonResponse(
                .ok,
                Components.Schemas.SavedShowStateResponse(
                    data: .init(isSaved: true)
                ),
                encoder: APIMockEncoder.make()
            )
        }
        let harness = makeHarness()
        let client = makeClient(transport: transport)

        let mutation = Task {
            await harness.store.setSaved(
                showId: 44,
                isSaved: true,
                apiClient: client,
                authManager: auth
            )
        }
        await gate.waitUntilSuspended()

        #expect(harness.store.value(for: 44) == true)
        #expect(harness.store.isPending(44) == true)

        await gate.release()
        #expect(await mutation.value == .updated(true))
        #expect(harness.store.isPending(44) == false)
    }

    @Test("permanent failure rolls the optimistic value back")
    func permanentFailureRollsBack() async {
        let auth = await makeAuth(accountId: "account-a")
        let transport = StubClientTransport { _, _, _, _ in
            (
                HTTPResponse(
                    status: .conflict,
                    headerFields: [.contentType: "application/json"]
                ),
                HTTPBody(#"{"error":"Only upcoming shows can be saved"}"#)
            )
        }
        let harness = makeHarness()

        let result = await harness.store.setSaved(
            showId: 55,
            isSaved: true,
            apiClient: makeClient(transport: transport),
            authManager: auth
        )

        #expect(result == .failure("Only upcoming shows can be saved"))
        #expect(harness.store.value(for: 55) == false)
        #expect(await harness.queue.operationCount == 0)
    }

    @Test("transient failure keeps optimistic state and replays from the queue")
    func transientFailureQueuesAndReplays() async {
        let auth = await makeAuth(accountId: "account-a")
        let attempts = AttemptCounter()
        let transport = StubClientTransport { _, _, _, operationID in
            #expect(operationID == Operations.SaveShow.id)
            if await attempts.next() == 1 {
                throw URLError(.notConnectedToInternet)
            }
            return jsonResponse(
                .ok,
                Components.Schemas.SavedShowStateResponse(
                    data: .init(isSaved: true)
                ),
                encoder: APIMockEncoder.make()
            )
        }
        let client = makeClient(transport: transport)
        let harness = makeHarness { operation in
            guard case .setSavedShow(let showId) = operation.type else {
                throw OfflineOperationError.terminal(reason: "Unexpected operation")
            }
            let payload = try JSONDecoder().decode(
                SavedShowMutationPayload.self,
                from: operation.payload
            )
            #expect(payload.showId == showId)
            let response = try await client.saveShow(path: .init(showId: showId))
            guard case .ok = response else {
                throw URLError(.badServerResponse)
            }
        }

        let result = await harness.store.setSaved(
            showId: 66,
            isSaved: true,
            apiClient: client,
            authManager: auth
        )

        #expect(result == .queued(true))
        #expect(harness.store.value(for: 66) == true)
        #expect(await harness.queue.operationCount == 1)

        await harness.queue.syncPendingOperations()

        #expect(await harness.queue.operationCount == 0)
        #expect(await attempts.count == 2)
    }

    @Test("queue identity coalesces one show without discarding another")
    func queueIdentityIncludesShowId() async throws {
        let harness = makeHarness()
        try await harness.queue.enqueue(
            type: .setSavedShow(showId: 1),
            payload: JSONEncoder().encode(
                SavedShowMutationPayload(showId: 1, isSaved: true)
            )
        )
        try await harness.queue.enqueue(
            type: .setSavedShow(showId: 2),
            payload: JSONEncoder().encode(
                SavedShowMutationPayload(showId: 2, isSaved: true)
            )
        )
        try await harness.queue.enqueue(
            type: .setSavedShow(showId: 1),
            payload: JSONEncoder().encode(
                SavedShowMutationPayload(showId: 1, isSaved: false)
            )
        )

        let pending = await harness.queue.pendingOperationsList
        #expect(pending.count == 2)
        let showOne = pending.first { $0.type == .setSavedShow(showId: 1) }
        let payload = try #require(showOne).payload
        #expect(try JSONDecoder().decode(SavedShowMutationPayload.self, from: payload).isSaved == false)
    }

    @Test("legacy queued comedian operation remains Codable")
    func legacyOperationCodableCompatibility() throws {
        let decoded = try JSONDecoder().decode(
            LaughTrackOfflineOperation.self,
            from: Data(#""toggleFavorite""#.utf8)
        )
        #expect(decoded == .toggleFavorite)
        #expect(
            String(
                decoding: try JSONEncoder().encode(decoded),
                as: UTF8.self
            ) == #""toggleFavorite""#
        )
    }

    @Test("reset clears account state caches and queued operations")
    func resetClearsAccountState() async throws {
        let auth = await makeAuth(accountId: "account-a")
        let harness = makeHarness()
        let client = makeClient(transport: StubClientTransport { _, _, _, operationID in
            if operationID == Operations.GetSavedShowState.id {
                return jsonResponse(
                    .ok,
                    Components.Schemas.SavedShowStateResponse(
                        data: .init(isSaved: true)
                    ),
                    encoder: APIMockEncoder.make()
                )
            }
            return jsonResponse(
                .ok,
                Components.Schemas.SavedShowListResponse(
                    data: [makeShow(id: 77)],
                    total: 1,
                    page: 1,
                    size: 20,
                    totalPages: 1
                ),
                encoder: APIMockEncoder.make()
            )
        })
        await harness.store.loadState(showId: 77, apiClient: client, authManager: auth)
        await harness.store.loadSavedShows(
            period: .upcoming,
            apiClient: client,
            authManager: auth
        )
        try await harness.queue.enqueue(
            type: .setSavedShow(showId: 77),
            payload: JSONEncoder().encode(
                SavedShowMutationPayload(showId: 77, isSaved: false)
            )
        )

        await harness.store.resetAccountState()

        #expect(harness.store.storedValue(for: 77) == nil)
        #expect(harness.store.upcomingPage == nil)
        #expect(harness.store.pastPage == nil)
        #expect(harness.store.upcomingPhase == .idle)
        #expect(await harness.queue.operationCount == 0)
    }

    @Test("signed-out mutation requests authentication without state or queue writes")
    func signedOutMutationRequestsAuthentication() async {
        let auth = await LaughTrackHostedViewTestSupport.makeAuthManager(
            name: "saved-show-signed-out"
        )
        let harness = makeHarness()

        let result = await harness.store.setSaved(
            showId: 88,
            isSaved: true,
            apiClient: makeClient(transport: .alwaysFails()),
            authManager: auth
        )

        guard case .signInRequired = result else {
            Issue.record("Expected sign-in requirement")
            return
        }
        #expect(harness.store.storedValue(for: 88) == nil)
        #expect(await harness.queue.operationCount == 0)
    }

    @Test("service registration exposes the saved-show store")
    func serviceRegistrationExposesStore() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        ServiceRegistration.configureOfflineQueue(
            container,
            apiClient: makeClient(transport: .alwaysSucceeds())
        )

        #expect(container.resolveOptional(SavedShowStore.self) != nil)
    }

    private func makeAuth(accountId: String) async -> AuthManager {
        let auth = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "saved-show-\(accountId)-\(UUID().uuidString)"
        )
        auth.loadUserRequest = {
            AuthenticatedUser(
                userId: accountId,
                displayName: accountId,
                email: "\(accountId)@example.com",
                avatarURL: nil
            )
        }
        await auth.refreshCurrentUser()
        return auth
    }

    private func makeHarness(
        executor: @escaping @Sendable (
            QueuedOperation<LaughTrackOfflineOperation>
        ) async throws -> Void = { _ in }
    ) -> (
        store: SavedShowStore,
        queue: OfflineOperationQueue<LaughTrackOfflineOperation>
    ) {
        let suiteName = "SavedShowStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let queue = OfflineOperationQueue<LaughTrackOfflineOperation>(
            storageKey: "saved-shows",
            userDefaults: defaults,
            networkMonitor: TestNetworkMonitor(),
            executor: executor
        )
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(suiteName, isDirectory: true)
        let store = SavedShowStore(
            cache: DataCache<LaughTrackCacheKey>(),
            persistentCache: PersistentMainPageCache(
                directory: directory,
                schemaVersion: "tests"
            ),
            offlineQueue: queue
        )
        return (store, queue)
    }
}

private func makeClient(transport: StubClientTransport) -> Client {
    Client(
        serverURL: URL(string: "https://example.com")!,
        configuration: .laughTrack,
        transport: transport
    )
}

private func makeShow(
    id: Int,
    date: Date = Date(timeIntervalSince1970: 300)
) -> Components.Schemas.Show {
    .init(
        id: id,
        clubId: 1,
        clubName: "Test Club",
        date: date,
        name: "Show \(id)",
        imageUrl: "https://example.com/show.png"
    )
}

private func jsonResponse<T: Encodable>(
    _ status: HTTPResponse.Status,
    _ value: T,
    encoder: JSONEncoder
) -> (HTTPResponse, HTTPBody?) {
    (
        HTTPResponse(
            status: status,
            headerFields: [.contentType: "application/json"]
        ),
        HTTPBody(try! encoder.encode(value))
    )
}

private func queryValue(_ name: String, from path: String?) -> String? {
    guard let path else { return nil }
    var components = URLComponents()
    components.path = "/"
    components.percentEncodedQuery = path
        .split(separator: "?", maxSplits: 1)
        .dropFirst()
        .first
        .map(String.init)
    return components.queryItems?.first { $0.name == name }?.value
}

private final class TestNetworkMonitor: NetworkMonitorProtocol, @unchecked Sendable {
    let isConnected = true
    let connectivityPublisher = Just(true).eraseToAnyPublisher()
}

private actor AttemptCounter {
    private(set) var count = 0

    func next() -> Int {
        count += 1
        return count
    }
}

private actor SuspensionGate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var suspended = false

    func suspend() async {
        suspended = true
        await withCheckedContinuation { continuation = $0 }
    }

    func waitUntilSuspended() async {
        while !suspended {
            await Task.yield()
        }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}
