import Foundation
import LaughTrackAPIClient
import LaughTrackBridge

#if canImport(UIKit)
import UIKit
#endif

public protocol PushDeviceTokenManaging: Sendable {
    func registerForRemoteNotifications() async
    func uploadDeviceToken(_ deviceToken: Data) async
    func deactivateCurrentDeviceToken() async
}

/// Routes push-token registration/deactivation through the generated OpenAPI
/// client (and thus TokenRefreshMiddleware), replacing the former hand-rolled
/// URLRequest client that built its own bearer header and so silently failed
/// after access-token expiry (TASK-3631).
public final class PushDeviceTokenManager: PushDeviceTokenManaging, @unchecked Sendable {
    private let apiClient: Client
    private let appStateStorage: AppStateStorageProtocol

    public init(
        apiClient: Client,
        appStateStorage: AppStateStorageProtocol
    ) {
        self.apiClient = apiClient
        self.appStateStorage = appStateStorage
    }

    public func registerForRemoteNotifications() async {
        #if canImport(UIKit)
        await MainActor.run {
            UIApplication.shared.registerForRemoteNotifications()
        }
        #endif
    }

    public func uploadDeviceToken(_ deviceToken: Data) async {
        let token = Self.hexString(from: deviceToken)
        guard !token.isEmpty else { return }

        do {
            let output = try await apiClient.registerMePushToken(
                .init(body: .json(.init(token: token, platform: .ios)))
            )
            switch output {
            case .ok:
                appStateStorage.setValue(token, forKey: StorageKey.currentDeviceToken)
            case .badRequest, .unauthorized, .unprocessableContent, .tooManyRequests, .undocumented:
                // Best-effort — leave the stored token untouched so a later
                // token callback or settings change retries the upload.
                break
            }
        } catch {
            // APNs refresh upload is best-effort; the system will deliver future
            // token callbacks and settings changes can trigger registration again.
        }
    }

    public func deactivateCurrentDeviceToken() async {
        guard let token = appStateStorage.getValue(
            forKey: StorageKey.currentDeviceToken,
            as: String.self
        ) else {
            return
        }

        do {
            _ = try await apiClient.deleteMePushToken(
                .init(body: .json(.init(token: token, platform: .ios)))
            )
        } catch {
            // Local opt-out/sign-out should proceed even if the server is offline.
        }
        appStateStorage.removeValue(forKey: StorageKey.currentDeviceToken)
    }

    private static func hexString(from data: Data) -> String {
        data.map { String(format: "%02x", $0) }.joined()
    }

    private enum StorageKey {
        static let currentDeviceToken = "laughtrack.notifications.current-device-token"
    }
}
