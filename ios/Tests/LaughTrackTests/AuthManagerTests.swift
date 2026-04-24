import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore
import LaughTrackAPIClient

@Suite("AuthManager")
struct AuthManagerTests {
    @Test("restoreSession marks a saved non-expired JWT as authenticated")
    @MainActor
    func restoreSessionAuthenticatesSavedToken() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.restore.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()

        try? tokenManager.storeTokens(
            accessToken: Self.jwt(expirationOffset: 3600),
            refreshToken: "opaque-refresh-token-\(UUID().uuidString)"
        )

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.restoreSession()

        guard case .authenticated(let session) = manager.state else {
            Issue.record("Expected authenticated state")
            return
        }

        #expect(session.expiresAt != nil)
        #expect(await authMiddleware.hasAccessToken)
    }

    @Test("signIn stores the returned access and refresh tokens as distinct values")
    @MainActor
    func signInStoresReturnedToken() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.signIn.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()
        let accessToken = Self.jwt(expirationOffset: 7200)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        runner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.signIn(with: .google)

        guard case .authenticated(let session) = manager.state else {
            Issue.record("Expected authenticated state")
            return
        }

        #expect(session.provider == .google)
        #expect(tokenManager.isAuthenticated)
        #expect(tokenManager.retrieveAccessToken() == accessToken)
        #expect(tokenManager.retrieveRefreshToken() == refreshToken)
        #expect(tokenManager.retrieveAccessToken() != tokenManager.retrieveRefreshToken())
        #expect(await authMiddleware.hasAccessToken)
    }

    @Test("restoreSession clears legacy installs that stored the access token in both slots")
    @MainActor
    func restoreSessionClearsLegacyDualAccessTokenInstall() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.legacy.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()

        let accessToken = Self.jwt(expirationOffset: 3600)
        try? tokenManager.storeTokens(accessToken: accessToken, refreshToken: accessToken)

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.restoreSession()

        #expect(manager.state == .signedOut(message: nil))
        #expect(!tokenManager.isAuthenticated)
        #expect(!(await authMiddleware.hasAccessToken))
    }

    @Test("restoreSession keeps an authenticated session even when the access token is expired")
    @MainActor
    func restoreSessionKeepsAuthWhenAccessExpiredButRefreshExists() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.expiredAccess.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()

        let expiredAccess = Self.jwt(expirationOffset: -60)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        try? tokenManager.storeTokens(accessToken: expiredAccess, refreshToken: refreshToken)

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.restoreSession()

        guard case .authenticated = manager.state else {
            Issue.record("Expected authenticated state — refresh token should keep session alive even with expired access token")
            return
        }
        #expect(await authMiddleware.hasAccessToken)
    }

    @Test("user-cancelled auth returns to signed out with a clear message")
    @MainActor
    func cancelledAuthReturnsNonDestructiveError() async {
        let secureStorage = InMemorySecureStorage()
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()
        runner.error = AuthFlowError.cancelled

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.cancel.\(UUID().uuidString)")!),
            oauthSessionRunner: runner
        )

        await manager.signIn(with: .apple)

        #expect(manager.state == .signedOut(message: "Sign-in was cancelled."))
        #expect(!tokenManager.isAuthenticated)
    }

    @Test("handleUnauthorizedResponse clears persisted auth state")
    @MainActor
    func unauthorizedResponseClearsAuth() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.unauthorized.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()

        try? tokenManager.storeTokens(
            accessToken: Self.jwt(expirationOffset: 3600),
            refreshToken: "opaque-refresh-token-\(UUID().uuidString)"
        )

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.restoreSession()
        await manager.handleUnauthorizedResponse()

        #expect(manager.state == .signedOut(message: "Your session expired. Sign in again."))
        #expect(!tokenManager.isAuthenticated)
        #expect(!(await authMiddleware.hasAccessToken))
    }

    private static func jwt(expirationOffset: TimeInterval) -> String {
        let header = #"{"alg":"HS256","typ":"JWT"}"#
        let payload = #"{"exp":\#(Int(Date().addingTimeInterval(expirationOffset).timeIntervalSince1970))}"#
        return "\(base64URL(header)).\(base64URL(payload)).signature"
    }

    private static func base64URL(_ string: String) -> String {
        Data(string.utf8)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

private final class MockOAuthSessionRunner: OAuthSessionRunning {
    var callbackURL = URL(string: "laughtrack://auth/callback")!
    var error: Error?

    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        if let error {
            throw error
        }
        return callbackURL
    }
}

private final class InMemorySecureStorage: SecureStorageProtocol {
    private var values: [String: String] = [:]

    func save(_ value: String, forKey key: String) throws {
        values[key] = value
    }

    func retrieve(forKey key: String) throws -> String? {
        values[key]
    }

    func delete(forKey key: String) throws {
        values[key] = nil
    }

    func deleteAll() throws {
        values.removeAll()
    }
}
