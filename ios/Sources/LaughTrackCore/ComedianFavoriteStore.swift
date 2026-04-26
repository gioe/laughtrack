import Combine
import Foundation
import LaughTrackAPIClient

@MainActor
public final class ComedianFavoriteStore: ObservableObject {
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

    @Published private var values: [String: Bool] = [:]
    @Published private var pending: Set<String> = []
    @Published public private(set) var savedFavoriteComedians: [Components.Schemas.ComedianSearchItem] = []
    @Published public private(set) var savedFavoritesPhase: SavedFavoritesPhase = .idle

    private var hasLoadedSavedFavorites = false

    public init() {}

    public func value(for uuid: String, fallback: Bool? = nil) -> Bool {
        values[uuid] ?? fallback ?? false
    }

    public func storedValue(for uuid: String) -> Bool? {
        values[uuid]
    }

    public func isPending(_ uuid: String) -> Bool {
        pending.contains(uuid)
    }

    public func resetSavedFavorites() {
        hasLoadedSavedFavorites = false
        savedFavoriteComedians = []
        savedFavoritesPhase = .idle
    }

    public func seed(uuid: String, value: Bool?) {
        guard let value, values[uuid] == nil else { return }
        values[uuid] = value
    }

    public func overwrite(uuid: String, value: Bool?) {
        guard let value else { return }
        values[uuid] = value
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
            let output = try await apiClient.getFavorites()
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                savedFavoriteComedians = response.data
                hasLoadedSavedFavorites = true
                response.data.forEach { comedian in
                    values[comedian.uuid] = true
                }
                savedFavoritesPhase = response.data.isEmpty ? .empty : .loaded
            case .unauthorized(let unauthorized):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unauthorized(
                    (try? unauthorized.body.json.error) ??
                        "Your session expired. Sign in again to load favorites."
                ))
            case .unprocessableContent(let invalidProfile):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(.unauthorized(
                    (try? invalidProfile.body.json.error) ??
                        "Your account needs to sign in again before loading favorites."
                ))
            case .internalServerError(let serverError):
                savedFavoritesPhase = .failure(.serverError(
                    status: 500,
                    message: (try? serverError.body.json.error)
                ))
            case .undocumented(let status, _):
                savedFavoritesPhase = .failure(classifyUndocumented(status: status, context: "favorites"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            savedFavoritesPhase = .failure(.network(
                "LaughTrack couldn’t reach the favorites service. Please try again."
            ))
        }
    }

    public func toggle(
        uuid: String,
        currentValue: Bool,
        apiClient: Client,
        authManager: AuthManager
    ) async -> ToggleResult {
        guard authManager.currentSession != nil else {
            return .signInRequired("Sign in from Settings to save favorite comedians.")
        }

        pending.insert(uuid)
        defer { pending.remove(uuid) }

        do {
            let response: Components.Schemas.FavoriteResponse
            if currentValue {
                let output = try await apiClient.removeFavorite(.init(path: .init(comedianId: uuid)))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            } else {
                let output = try await apiClient.addFavorite(.init(body: .json(.init(comedianId: uuid))))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            }

            let nextValue = response.data.isFavorited
            values[uuid] = nextValue
            if nextValue {
                if let index = savedFavoriteComedians.firstIndex(where: { $0.uuid == uuid }) {
                    savedFavoriteComedians[index].isFavorite = true
                }
            } else {
                savedFavoriteComedians.removeAll { $0.uuid == uuid }
                if savedFavoriteComedians.isEmpty, hasLoadedSavedFavorites {
                    savedFavoritesPhase = .empty
                }
            }
            return .updated(nextValue)
        } catch {
            return .failure("LaughTrack couldn’t reach the favorites service. Please try again.")
        }
    }
}
