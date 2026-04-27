import Foundation
import LaughTrackBridge
import LaughTrackAPIClient

public enum ServiceRegistration {
    @MainActor
    public static func configure(_ container: ServiceContainer) {
        container.register(NetworkMonitorProtocol.self, scope: .appLevel) { NetworkMonitor.shared }
        container.register(SecureStorageProtocol.self, scope: .appLevel) { KeychainStorage() }
        container.register(ToastManager.self, scope: .featureLevel) { ToastManager() }
        container.register(ImageCache.self, scope: .appLevel) { ImageCache() }
        container.register(AppStateStorageProtocol.self, scope: .appLevel) { AppStateStorage() }

        container.register(DataCache<LaughTrackCacheKey>.self, scope: .appLevel) { DataCache<LaughTrackCacheKey>() }

        container.register(NearbyPreferenceStore.self, scope: .appLevel) {
            NearbyPreferenceStore(
                appStateStorage: container.resolve(AppStateStorageProtocol.self)
            )
        }
        container.register((any NearbyLocationResolving).self, scope: .appLevel) {
            CurrentLocationZipResolver()
        }
        container.register(NearbyLocationController.self, scope: .appLevel) {
            NearbyLocationController(
                store: container.resolve(NearbyPreferenceStore.self),
                resolver: container.resolve((any NearbyLocationResolving).self),
                zipLocationResolver: container.resolve((any ZipLocationResolving).self)
            )
        }
    }

    @MainActor
    public static func configureZipLocationResolver(_ container: ServiceContainer, apiClient: Client) {
        container.register((any ZipLocationResolving).self, scope: .appLevel) {
            APIZipLocationResolver(apiClient: apiClient)
        }
    }

    @MainActor
    public static func configureOfflineQueue(_ container: ServiceContainer, apiClient: Client) {
        container.register(OfflineOperationQueue<LaughTrackOfflineOperation>.self, scope: .appLevel) {
            OfflineOperationQueue<LaughTrackOfflineOperation>(
                storageKey: "laughtrack.offline",
                executor: { op in
                    let payload = try JSONDecoder().decode(ToggleFavoritePayload.self, from: op.payload)
                    switch op.type {
                    case .toggleFavorite:
                        // 4xx responses (badRequest/unauthorized/notFound/unprocessableContent) are
                        // terminal — retrying will never succeed, so throw OfflineOperationError.terminal
                        // so the queue's fail-fast path routes the op straight to failedOperations
                        // instead of burning the 30s retry/backoff budget. 5xx (.internalServerError) and
                        // unknown statuses (.undocumented) throw URLError(.badServerResponse) so the queue
                        // retries with backoff.
                        if payload.isFavorite {
                            let response = try await apiClient.addFavorite(
                                .init(body: .json(.init(comedianId: payload.comedianId)))
                            )
                            switch response {
                            case .ok:
                                break
                            case .badRequest:
                                throw OfflineOperationError.terminal(reason: "addFavorite returned 400 Bad Request")
                            case .unauthorized:
                                throw OfflineOperationError.terminal(reason: "addFavorite returned 401 Unauthorized")
                            case .notFound:
                                throw OfflineOperationError.terminal(reason: "addFavorite returned 404 Not Found")
                            case .unprocessableContent:
                                throw OfflineOperationError.terminal(reason: "addFavorite returned 422 Unprocessable Content")
                            case .internalServerError, .undocumented:
                                throw URLError(.badServerResponse)
                            }
                        } else {
                            let response = try await apiClient.removeFavorite(
                                .init(path: .init(comedianId: payload.comedianId))
                            )
                            switch response {
                            case .ok:
                                break
                            case .badRequest:
                                throw OfflineOperationError.terminal(reason: "removeFavorite returned 400 Bad Request")
                            case .unauthorized:
                                throw OfflineOperationError.terminal(reason: "removeFavorite returned 401 Unauthorized")
                            case .notFound:
                                throw OfflineOperationError.terminal(reason: "removeFavorite returned 404 Not Found")
                            case .unprocessableContent:
                                throw OfflineOperationError.terminal(reason: "removeFavorite returned 422 Unprocessable Content")
                            case .internalServerError, .undocumented:
                                throw URLError(.badServerResponse)
                            }
                        }
                    }
                }
            )
        }
    }
}
