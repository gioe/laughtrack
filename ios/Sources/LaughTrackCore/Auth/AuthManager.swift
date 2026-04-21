import Combine
import Foundation
import LaughTrackBridge
import LaughTrackAPIClient

@MainActor
public final class AuthManager: ObservableObject {
    public enum State: Equatable {
        case restoring
        case signedOut(message: String?)
        case signingIn(AuthProvider)
        case authenticated(AuthSessionMetadata)
    }

    @Published public private(set) var state: State = .restoring

    public var currentSession: AuthSessionMetadata? {
        guard case .authenticated(let session) = state else { return nil }
        return session
    }

    private let tokenManager: AuthTokenManager
    private let authMiddleware: AuthenticationMiddleware
    private let appStateStorage: AppStateStorageProtocol
    private let oauthSessionRunner: any OAuthSessionRunning
    private var hasRestoredSession = false

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

        if let expirationDate = Self.extractExpirationDate(from: accessToken), expirationDate <= Date() {
            await clearSession(message: "Your session expired. Sign in again.")
            return
        }

        let refreshToken = tokenManager.retrieveRefreshToken() ?? accessToken
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

            guard let token = Self.extractQueryValue(named: "token", from: callbackURL) else {
                let errorMessage = Self.extractQueryValue(named: "error", from: callbackURL)
                state = .signedOut(message: Self.message(for: errorMessage))
                return
            }

            await storeSession(token: token, provider: provider)
        } catch let error as AuthFlowError {
            state = .signedOut(message: error.errorDescription)
        } catch {
            state = .signedOut(message: Self.message(for: nil))
        }
    }

    public func signOut() async {
        await clearSession(message: nil)
    }

    public func handleUnauthorizedResponse() async {
        guard case .authenticated = state else { return }
        await clearSession(message: "Your session expired. Sign in again.")
    }

    private func storeSession(token: String, provider: AuthProvider) async {
        do {
            try tokenManager.storeTokens(accessToken: token, refreshToken: token)
            await authMiddleware.setTokens(accessToken: token, refreshToken: token)

            let metadata = AuthSessionMetadata(
                provider: provider,
                signedInAt: Date(),
                expiresAt: Self.extractExpirationDate(from: token)
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
        let callbackURL = websiteBaseURL
            .appendingPathComponent("api")
            .appendingPathComponent("v1")
            .appendingPathComponent("auth")
            .appendingPathComponent("native")
            .appendingPathComponent("callback")

        var callbackComponents = URLComponents(
            url: callbackURL,
            resolvingAgainstBaseURL: false
        )!
        callbackComponents.queryItems = [
            URLQueryItem(name: "provider", value: provider.rawValue)
        ]

        var components = URLComponents(
            url: websiteBaseURL
                .appendingPathComponent("api")
                .appendingPathComponent("auth")
                .appendingPathComponent("signin")
                .appendingPathComponent(provider.rawValue),
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = [
            URLQueryItem(name: "callbackUrl", value: callbackComponents.url?.absoluteString)
        ]
        return components.url!
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

    private static let callbackScheme = "laughtrack"
    private static let websiteBaseURL = URL(string: "https://laughtrack.app")!
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
