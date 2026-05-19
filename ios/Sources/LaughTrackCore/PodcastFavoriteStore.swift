import Combine
import Foundation
import LaughTrackAPIClient

@MainActor
public final class PodcastFavoriteStore: ObservableObject {
    public enum ToggleResult {
        case updated(Bool)
        case signInRequired(String)
        case failure(String)
    }

    public enum SavedFavoritesPhase: Equatable {
        case idle
        case loading
        case loaded
        case empty
        case failure(LoadFailure)
    }

    @Published private var values: [Int: Bool] = [:]
    @Published var pending: Set<Int> = []
    @Published public private(set) var savedFavoritePodcasts: [Components.Schemas.FavoritePodcastItem] = []
    @Published public private(set) var savedFavoritesPhase: SavedFavoritesPhase = .idle

    private var hasLoadedSavedFavorites = false

    public init() {}

    public func value(for podcastID: Int, fallback: Bool? = nil) -> Bool {
        values[podcastID] ?? fallback ?? false
    }

    public func storedValue(for podcastID: Int) -> Bool? {
        values[podcastID]
    }

    public func isPending(_ podcastID: Int) -> Bool {
        pending.contains(podcastID)
    }

    public func resetSavedFavorites() {
        hasLoadedSavedFavorites = false
        savedFavoritePodcasts = []
        savedFavoritesPhase = .idle
        values = [:]
        pending = []
    }

    public func seed(podcastID: Int, value: Bool?) {
        guard let value, values[podcastID] == nil else { return }
        values[podcastID] = value
    }

    public func overwrite(podcastID: Int, value: Bool?) {
        guard let value else { return }
        values[podcastID] = value
    }

    public func loadSavedFavorites(
        apiClient: Client,
        authManager: AuthManager,
        force: Bool = false
    ) async {
        guard authManager.currentSession != nil else {
            resetSavedFavorites()
            return
        }
        if hasLoadedSavedFavorites && !force {
            return
        }

        savedFavoritesPhase = .loading

        do {
            let output = try await apiClient.getFavoritePodcasts()
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                savedFavoritePodcasts = response.data
                hasLoadedSavedFavorites = true
                response.data.forEach { podcast in
                    values[podcast.id] = true
                }
                savedFavoritesPhase = response.data.isEmpty ? .empty : .loaded
            case .unauthorized(let unauthorized):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unauthorized(
                    (try? unauthorized.body.json.error) ??
                        "Your session expired. Sign in again to load podcast favorites."
                ))
            case .unprocessableContent(let invalidProfile):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unexpected(
                    status: 422,
                    message: (try? invalidProfile.body.json.error) ??
                        "Your account needs to sign in again before loading podcast favorites."
                ))
            case .internalServerError(let serverError):
                savedFavoritesPhase = .failure(.serverError(
                    status: 500,
                    message: (try? serverError.body.json.error)
                ))
            case .undocumented(let status, _):
                savedFavoritesPhase = .failure(classifyUndocumented(status: status, context: "favorite podcasts"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            savedFavoritesPhase = .failure(.network(
                "LaughTrack couldn’t reach the podcast favorites service. Please try again."
            ))
        }
    }

    public func toggle(
        podcastID: Int,
        currentValue: Bool,
        apiClient: Client,
        authManager: AuthManager
    ) async -> ToggleResult {
        guard authManager.currentSession != nil else {
            return .signInRequired("Sign in from Settings to save favorite podcasts.")
        }

        pending.insert(podcastID)
        defer { pending.remove(podcastID) }

        do {
            let response: Components.Schemas.FavoriteResponse
            if currentValue {
                let output = try await apiClient.removeFavoritePodcast(.init(path: .init(podcastId: podcastID)))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That podcast could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            } else {
                let output = try await apiClient.addFavoritePodcast(.init(body: .json(.init(podcastId: podcastID))))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That podcast could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            }

            let nextValue = response.data.isFavorited
            values[podcastID] = nextValue
            if !nextValue {
                savedFavoritePodcasts.removeAll { $0.id == podcastID }
                if savedFavoritePodcasts.isEmpty, hasLoadedSavedFavorites {
                    savedFavoritesPhase = .empty
                }
            }
            return .updated(nextValue)
        } catch {
            return .failure("LaughTrack couldn’t reach the podcast favorites service. Please try again.")
        }
    }
}
