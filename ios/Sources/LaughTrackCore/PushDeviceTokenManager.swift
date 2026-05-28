import Foundation
import LaughTrackBridge

#if canImport(UIKit)
import UIKit
#endif

public protocol PushDeviceTokenManaging: Sendable {
    func registerForRemoteNotifications() async
    func uploadDeviceToken(_ deviceToken: Data) async
    func deactivateCurrentDeviceToken() async
}

public final class PushDeviceTokenManager: PushDeviceTokenManaging, @unchecked Sendable {
    private let baseURL: URL
    private let tokenManager: AuthTokenManager
    private let appStateStorage: AppStateStorageProtocol
    private let urlSession: URLSession

    public init(
        baseURL: URL = AppConfiguration.apiBaseURL,
        tokenManager: AuthTokenManager,
        appStateStorage: AppStateStorageProtocol,
        urlSession: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.tokenManager = tokenManager
        self.appStateStorage = appStateStorage
        self.urlSession = urlSession
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
            try await send(method: "POST", token: token)
            appStateStorage.setValue(token, forKey: StorageKey.currentDeviceToken)
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
            try await send(method: "DELETE", token: token)
        } catch {
            // Local opt-out/sign-out should proceed even if the server is offline.
        }
        appStateStorage.removeValue(forKey: StorageKey.currentDeviceToken)
    }

    private func send(method: String, token: String) async throws {
        let accessToken = await MainActor.run { tokenManager.retrieveAccessToken() }
        guard let accessToken else {
            throw URLError(.userAuthenticationRequired)
        }

        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/me/push-tokens"))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONSerialization.data(
            withJSONObject: ["token": token, "platform": "ios"],
            options: []
        )

        let (_, response) = try await urlSession.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode)
        else {
            throw URLError(.badServerResponse)
        }
    }

    private static func hexString(from data: Data) -> String {
        data.map { String(format: "%02x", $0) }.joined()
    }

    private enum StorageKey {
        static let currentDeviceToken = "laughtrack.notifications.current-device-token"
    }
}
