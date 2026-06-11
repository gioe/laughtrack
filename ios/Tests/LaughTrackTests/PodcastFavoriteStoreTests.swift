import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
@testable import LaughTrackAPIClient
@testable import LaughTrackCore

@Suite("PodcastFavoriteStore")
@MainActor
struct PodcastFavoriteStoreTests {
    @Test("first add-toggle force-refreshes the saved list so the Favorites tab gate sees the new favorite")
    func firstAddToggleRefreshesSavedFavorites() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "podcast-fav-first-add-refresh"
        )
        let store = PodcastFavoriteStore()
        let transport = FavoritePodcastMockTransport(
            listResponses: [
                .init(data: []),
                .init(data: [
                    .init(id: 30, title: "Working It Out", episodeCount: 12, isFavorite: true),
                ]),
            ]
        )
        let apiClient = makeClient(transport: transport)

        // Fresh-user sign-in hydration: the server has no favorites yet.
        await store.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        #expect(store.savedFavoritePodcasts.isEmpty)
        #expect(store.savedFavoritesPhase == .empty)

        let result = await store.toggle(
            podcastID: 30,
            currentValue: false,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(true) = result else {
            Issue.record("Expected .updated(true), got \(result)")
            return
        }
        #expect(store.savedFavoritePodcasts.map(\.id) == [30])
        #expect(store.savedFavoritesPhase == .loaded)
        #expect(transport.listCallCount == 2)
    }

    @Test("add-toggle for a podcast already in the saved list does not re-fetch")
    func addToggleForAlreadySavedPodcastDoesNotRefetch() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "podcast-fav-in-place-add"
        )
        let store = PodcastFavoriteStore()
        let transport = FavoritePodcastMockTransport(
            listResponses: [
                .init(data: [
                    .init(id: 30, title: "Working It Out", episodeCount: 12, isFavorite: true),
                ]),
            ]
        )
        let apiClient = makeClient(transport: transport)

        await store.loadSavedFavorites(apiClient: apiClient, authManager: authManager)

        let result = await store.toggle(
            podcastID: 30,
            currentValue: false,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(true) = result else {
            Issue.record("Expected .updated(true), got \(result)")
            return
        }
        #expect(store.savedFavoritePodcasts.map(\.id) == [30])
        #expect(transport.listCallCount == 1)
    }

    @Test("remove-toggle drops the podcast from the saved list and flips phase to empty")
    func removeToggleDropsPodcastFromSavedList() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "podcast-fav-remove"
        )
        let store = PodcastFavoriteStore()
        let transport = FavoritePodcastMockTransport(
            listResponses: [
                .init(data: [
                    .init(id: 30, title: "Working It Out", episodeCount: 12, isFavorite: true),
                ]),
            ]
        )
        let apiClient = makeClient(transport: transport)

        await store.loadSavedFavorites(apiClient: apiClient, authManager: authManager)
        #expect(store.savedFavoritePodcasts.map(\.id) == [30])

        let result = await store.toggle(
            podcastID: 30,
            currentValue: true,
            apiClient: apiClient,
            authManager: authManager
        )

        guard case .updated(false) = result else {
            Issue.record("Expected .updated(false), got \(result)")
            return
        }
        #expect(store.savedFavoritePodcasts.isEmpty)
        #expect(store.savedFavoritesPhase == .empty)
    }

    private func makeClient(transport: FavoritePodcastMockTransport) -> Client {
        Client(
            serverURL: URL(string: "https://example.com")!,
            configuration: .laughTrack,
            transport: transport
        )
    }
}

/// Serves a fixed sequence of list responses (clamped to the last entry once
/// exhausted) and counts how many were requested, so tests can model a server
/// whose favorites list changes between fetches — e.g. empty at sign-in
/// hydration, populated after an add — and assert on fetch counts. Lock-guarded
/// because ClientTransport.send is nonisolated.
private final class ListResponseSequencer<Response>: @unchecked Sendable {
    private let lock = NSLock()
    private let responses: [Response]
    private var served = 0

    init(_ responses: [Response]) {
        precondition(!responses.isEmpty, "ListResponseSequencer needs at least one response")
        self.responses = responses
    }

    func next() -> Response {
        lock.lock()
        defer { lock.unlock() }
        let response = responses[min(served, responses.count - 1)]
        served += 1
        return response
    }

    var callCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return served
    }
}

/// Mock transport for the three podcast-favorite operations
/// (`getFavoritePodcasts`, `addFavoritePodcast`, `removeFavoritePodcast`).
/// Each test instantiates its own transport; behavior is fixed at init time so
/// a test reading captured state never races against handler swaps.
private struct FavoritePodcastMockTransport: ClientTransport {
    private let listResponses: ListResponseSequencer<Components.Schemas.FavoritePodcastListResponse>
    /// Value returned in `FavoriteResponse.data.isFavorited` when the test
    /// drives the add path. Defaults to `true` (the production server's
    /// contract on success).
    let isFavoritedForAdd: Bool
    /// Value returned on the remove path. Defaults to `false`.
    let isFavoritedForRemove: Bool

    init(
        listResponses: [Components.Schemas.FavoritePodcastListResponse] = [.init(data: [])],
        isFavoritedForAdd: Bool = true,
        isFavoritedForRemove: Bool = false
    ) {
        self.listResponses = ListResponseSequencer(listResponses)
        self.isFavoritedForAdd = isFavoritedForAdd
        self.isFavoritedForRemove = isFavoritedForRemove
    }

    var listCallCount: Int {
        listResponses.callCount
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = APIMockEncoder.make()

        switch operationID {
        case "getFavoritePodcasts":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(listResponses.next()))
            )
        case "addFavoritePodcast":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(
                    Components.Schemas.FavoriteResponse(data: .init(isFavorited: isFavoritedForAdd))
                ))
            )
        case "removeFavoritePodcast":
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
