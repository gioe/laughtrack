import Combine
import Foundation
import LaughTrackAPIClient

@MainActor
public final class ClubFavoriteStore: ObservableObject {
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
    @Published public private(set) var savedFavoriteClubs: [Components.Schemas.FavoriteClubItem] = []
    @Published public private(set) var savedFavoritesPhase: SavedFavoritesPhase = .idle

    private var hasLoadedSavedFavorites = false

    public init() {}

    public func value(for clubID: Int, fallback: Bool? = nil) -> Bool {
        values[clubID] ?? fallback ?? false
    }

    public func storedValue(for clubID: Int) -> Bool? {
        values[clubID]
    }

    public func isPending(_ clubID: Int) -> Bool {
        pending.contains(clubID)
    }

    public func resetSavedFavorites() {
        hasLoadedSavedFavorites = false
        savedFavoriteClubs = []
        savedFavoritesPhase = .idle
        values = [:]
        pending = []
    }

    public func seed(clubID: Int, value: Bool?) {
        guard let value, values[clubID] == nil else { return }
        values[clubID] = value
    }

    public func overwrite(clubID: Int, value: Bool?) {
        guard let value else { return }
        values[clubID] = value
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
            let output = try await apiClient.getFavoriteClubs()
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                savedFavoriteClubs = response.data
                hasLoadedSavedFavorites = true
                response.data.forEach { club in
                    values[club.id] = true
                }
                savedFavoritesPhase = response.data.isEmpty ? .empty : .loaded
            case .unauthorized(let unauthorized):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unauthorized(
                    (try? unauthorized.body.json.error) ??
                        "Your session expired. Sign in again to load club favorites."
                ))
            case .unprocessableContent(let invalidProfile):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unexpected(
                    status: 422,
                    message: (try? invalidProfile.body.json.error) ??
                        "Your account needs to sign in again before loading club favorites."
                ))
            case .internalServerError(let serverError):
                savedFavoritesPhase = .failure(.serverError(
                    status: 500,
                    message: (try? serverError.body.json.error)
                ))
            case .undocumented(let status, _):
                savedFavoritesPhase = .failure(classifyUndocumented(status: status, context: "favorite clubs"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            savedFavoritesPhase = .failure(.network(
                "LaughTrack couldn’t reach the club favorites service. Please try again."
            ))
        }
    }

    public func toggle(
        clubID: Int,
        currentValue: Bool,
        apiClient: Client,
        authManager: AuthManager
    ) async -> ToggleResult {
        guard authManager.currentSession != nil else {
            return .signInRequired("Sign in from Settings to save favorite clubs.")
        }

        pending.insert(clubID)
        defer { pending.remove(clubID) }

        do {
            let response: Components.Schemas.FavoriteResponse
            if currentValue {
                let output = try await apiClient.removeFavoriteClub(.init(path: .init(clubId: clubID)))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            } else {
                let output = try await apiClient.addFavoriteClub(.init(body: .json(.init(clubId: clubID))))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That club could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            }

            let nextValue = response.data.isFavorited
            values[clubID] = nextValue
            if !nextValue {
                savedFavoriteClubs.removeAll { $0.id == clubID }
                if savedFavoriteClubs.isEmpty, hasLoadedSavedFavorites {
                    savedFavoritesPhase = .empty
                }
            }
            return .updated(nextValue)
        } catch {
            return .failure("LaughTrack couldn’t reach the club favorites service. Please try again.")
        }
    }
}
