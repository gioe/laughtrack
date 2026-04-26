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
        container.register((any ZipLocationResolving).self, scope: .appLevel) {
            APIZipLocationResolver()
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
    public static func configureOfflineQueue(_ container: ServiceContainer, apiClient: Client) {
        container.register(OfflineOperationQueue<LaughTrackOfflineOperation>.self, scope: .appLevel) {
            OfflineOperationQueue<LaughTrackOfflineOperation>(
                storageKey: "laughtrack.offline",
                executor: { op in
                    let payload = try JSONDecoder().decode(ToggleFavoritePayload.self, from: op.payload)
                    switch op.type {
                    case .toggleFavorite:
                        if payload.isFavorite {
                            _ = try await apiClient.addFavorite(
                                .init(body: .json(.init(comedianId: payload.comedianId)))
                            )
                        } else {
                            _ = try await apiClient.removeFavorite(
                                .init(path: .init(comedianId: payload.comedianId))
                            )
                        }
                    }
                }
            )
        }
    }
}
