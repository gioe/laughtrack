import Combine
import Foundation
import LaughTrackBridge
import LaughTrackAPIClient
import os

@MainActor
public final class AuthManager: ObservableObject {
    public enum State: Equatable {
        case restoring
        case signedOut(message: String?)
        case signingIn(AuthProvider)
        case authenticated(AuthSessionMetadata)
    }

    public typealias SignoutRequest = @Sendable () async throws -> Void

    @Published public private(set) var state: State = .restoring

    public var currentSession: AuthSessionMetadata? {
        guard case .authenticated(let session) = state else { return nil }
        return session
    }

    // Bound after construction in AppBootstrap, because the apiClient that
    // performs the server-side revocation is built after AuthManager (its
    // middlewares capture authManager). Left nil in tests that don't exercise
    // the server sign-out path.
    public var signoutRequest: SignoutRequest?

    private let tokenManager: AuthTokenManager
    private let authMiddleware: AuthenticationMiddleware
    private let appStateStorage: AppStateStorageProtocol
    private let oauthSessionRunner: any OAuthSessionRunning
    private var hasRestoredSession = false
    private static let logger = Logger(
        subsystem: "com.laughtrack.auth",
        category: "AuthManager"
    )

    public init(
        tokenManager: AuthTokenManager,
        authMiddleware: AuthenticationMiddleware,
        appStateStorage: AppStateStorageProtocol,
        oauthSessionRunner: any OAuthSessionRunning
    ) {
        self.tokenManager = tokenManager
        self.authMiddleware = authMiddleware
        self.appStateStorage = appStateStorage
        self.oauthSessionRunner = oauthSessionRunner
    }

    public func restoreSessionIfNeeded() async {
        guard !hasRestoredSession else { return }
        hasRestoredSession = true
        await restoreSession()
    }

    public func restoreSession() async {
        guard let accessToken = tokenManager.retrieveAccessToken() else {
            state = .signedOut(message: nil)
            return
        }

        // Pre-rotation builds (TASK-1724) saved the access token in both keychain
        // slots. Force re-auth for those installs rather than letting the access
        // token be replayed against /auth/refresh.
        guard let refreshToken = tokenManager.retrieveRefreshToken(),
              refreshToken != accessToken else {
            await clearSession(message: nil)
            return
        }

        await authMiddleware.setTokens(
            accessToken: accessToken,
            refreshToken: refreshToken
        )

        let storedSession = appStateStorage.getValue(
            forKey: StorageKey.sessionMetadata,
            as: AuthSessionMetadata.self
        ) ?? AuthSessionMetadata(
            provider: nil,
            signedInAt: Date(),
            expiresAt: Self.extractExpirationDate(from: accessToken)
        )

        state = .authenticated(storedSession)
    }

    public func signIn(with provider: AuthProvider) async {
        state = .signingIn(provider)

        do {
            let callbackURL = try await oauthSessionRunner.authenticate(
                startURL: Self.makeSignInURL(for: provider),
                callbackScheme: Self.callbackScheme
            )

            guard
                let accessToken = Self.extractQueryValue(named: "accessToken", from: callbackURL),
                let refreshToken = Self.extractQueryValue(named: "refreshToken", from: callbackURL)
            else {
                let errorMessage = Self.extractQueryValue(named: "error", from: callbackURL)
                state = .signedOut(message: Self.message(for: errorMessage))
                return
            }

            await storeSession(accessToken: accessToken, refreshToken: refreshToken, provider: provider)
        } catch let error as AuthFlowError {
            state = .signedOut(message: error.errorDescription)
        } catch {
            state = .signedOut(message: Self.message(for: nil))
        }
    }

    public func signOut() async {
        // Revoke server-side refresh tokens while we still have a valid Bearer
        // access token. Transport or auth failures must not block the local
        // clear — the user expects to end up signed out regardless.
        if let signoutRequest {
            do {
                try await signoutRequest()
            } catch {
                Self.logger.error(
                    "Server sign-out failed; clearing local session anyway: \(String(describing: error), privacy: .public)"
                )
            }
        }
        await clearSession(message: nil)
    }

    public func handleUnauthorizedResponse() async {
        guard case .authenticated = state else { return }
        await clearSession(message: "Your session expired. Sign in again.")
    }

    private func storeSession(accessToken: String, refreshToken: String, provider: AuthProvider) async {
        do {
            try tokenManager.storeTokens(accessToken: accessToken, refreshToken: refreshToken)
            await authMiddleware.setTokens(accessToken: accessToken, refreshToken: refreshToken)

            let metadata = AuthSessionMetadata(
                provider: provider,
                signedInAt: Date(),
                expiresAt: Self.extractExpirationDate(from: accessToken)
            )
            appStateStorage.setValue(metadata, forKey: StorageKey.sessionMetadata)
            state = .authenticated(metadata)
        } catch {
            await authMiddleware.clearTokens()
            state = .signedOut(message: "LaughTrack couldn’t save your session securely. Please try again.")
        }
    }

    private func clearSession(message: String?) async {
        do {
            try tokenManager.clearTokens()
        } catch {
            // Keep going so the app still returns to a safe signed-out state.
        }

        await authMiddleware.clearTokens()
        appStateStorage.removeValue(forKey: StorageKey.sessionMetadata)
        state = .signedOut(message: message)
    }

    private static func makeSignInURL(for provider: AuthProvider) -> URL {
        AuthRouteConfiguration.signInURL(for: provider)
    }

    private static func extractQueryValue(named name: String, from url: URL) -> String? {
        URLComponents(url: url, resolvingAgainstBaseURL: false)?
            .queryItems?
            .first(where: { $0.name == name })?
            .value
    }

    private static func message(for errorCode: String?) -> String {
        guard let errorCode else {
            return "Sign-in failed. Please try again."
        }

        let normalized = errorCode.lowercased()
        if normalized == "accessdenied" || normalized == "user_cancelled" {
            return "Sign-in was cancelled."
        }

        if normalized.hasPrefix("token_exchange_failed") || normalized == "missing_token" {
            return "Sign-in finished in the browser, but LaughTrack couldn’t create the mobile session. Please try again."
        }

        return "Sign-in failed. Please try again."
    }

    private static func extractExpirationDate(from token: String) -> Date? {
        let segments = token.split(separator: ".")
        guard segments.count == 3 else { return nil }

        var payload = String(segments[1])
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")

        let padding = payload.count % 4
        if padding != 0 {
            payload += String(repeating: "=", count: 4 - padding)
        }

        guard
            let data = Data(base64Encoded: payload),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let seconds = object["exp"] as? TimeInterval
        else {
            return nil
        }

        return Date(timeIntervalSince1970: seconds)
    }

    private enum StorageKey {
        static let sessionMetadata = "laughtrack.auth.session-metadata"
    }

    private static let callbackScheme = AuthRouteConfiguration.callbackScheme
}

public struct AuthSessionMetadata: Codable, Equatable, Sendable {
    public let provider: AuthProvider?
    public let signedInAt: Date
    public let expiresAt: Date?

    public init(provider: AuthProvider?, signedInAt: Date, expiresAt: Date?) {
        self.provider = provider
        self.signedInAt = signedInAt
        self.expiresAt = expiresAt
    }
}
