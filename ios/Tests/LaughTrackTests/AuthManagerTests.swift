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

    @Test("native email auth provider starts expected magic-link flow")
    @MainActor
    func nativeEmailAuthProviderStartsExpectedFlow() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.email.\(UUID().uuidString)")!)
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = MockOAuthSessionRunner()
        let accessToken = Self.jwt(expirationOffset: 7200)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        runner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=email&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!

        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )

        await manager.signIn(with: .email)

        let startComponents = runner.lastStartURL.flatMap {
            URLComponents(url: $0, resolvingAgainstBaseURL: false)
        }
        let callbackURL = startComponents?.queryItems?.first(where: { $0.name == "callbackUrl" })?.value
        let callbackComponents = callbackURL
            .flatMap(URL.init(string:))
            .flatMap { URLComponents(url: $0, resolvingAgainstBaseURL: false) }

        #expect(runner.lastCallbackScheme == "laughtrack")
        #expect(startComponents?.path.isEmpty == true)
        #expect(startComponents?.queryItems?.first(where: { $0.name == "nativeAuthProvider" })?.value == "email")
        #expect(callbackComponents?.path == "/api/v1/auth/native/callback")
        #expect(callbackComponents?.queryItems?.first(where: { $0.name == "provider" })?.value == "email")

        guard case .authenticated(let session) = manager.state else {
            Issue.record("Expected authenticated state")
            return
        }
        #expect(session.provider == .email)
        #expect(tokenManager.retrieveAccessToken() == accessToken)
        #expect(tokenManager.retrieveRefreshToken() == refreshToken)
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

    @Test("signOut calls the server signout before clearing the local keychain")
    @MainActor
    func signOutCallsServerSignoutBeforeClearingTokens() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.signOutHappy.\(UUID().uuidString)")!)
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

        let recorder = SignoutRecorder()
        manager.signoutRequest = { [authMiddleware] in
            let hadToken = await authMiddleware.hasAccessToken
            await recorder.record(hadAccessToken: hadToken)
        }

        await manager.signOut()

        #expect(await recorder.callCount == 1)
        #expect(await recorder.observedAccessToken == true)
        #expect(manager.state == .signedOut(message: nil))
        #expect(!tokenManager.isAuthenticated)
        #expect(!(await authMiddleware.hasAccessToken))
    }

    @Test("signOut still clears local session when the server signout throws")
    @MainActor
    func signOutClearsLocalWhenServerSignoutFails() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.signOutFail.\(UUID().uuidString)")!)
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

        let recorder = SignoutRecorder()
        manager.signoutRequest = {
            await recorder.record(hadAccessToken: true)
            throw URLError(.networkConnectionLost)
        }

        // Pin the catch-block log emission to a recorder so a regression that
        // silently swallowed the thrown error (without calling the seam) would
        // be caught in addition to the post-condition assertions below.
        let errorRecorder = SignoutErrorRecorder()
        manager.signoutErrorObserver = { error in
            await errorRecorder.record(error: error)
        }

        await manager.signOut()

        #expect(await recorder.callCount == 1)
        #expect(manager.state == .signedOut(message: nil))
        #expect(!tokenManager.isAuthenticated)
        #expect(!(await authMiddleware.hasAccessToken))

        #expect(await errorRecorder.callCount == 1)
        let observed = await errorRecorder.lastError as? URLError
        #expect(observed?.code == .networkConnectionLost)
    }

    @Test("restoreSession invokes loadUserRequest and publishes the returned user")
    @MainActor
    func restoreSessionLoadsCurrentUser() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.loadUser.\(UUID().uuidString)")!)
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

        let recorder = LoadUserRecorder()
        let expected = AuthenticatedUser(
            displayName: "Ada Lovelace",
            email: "ada@example.com",
            avatarURL: URL(string: "https://cdn.example.com/avatar.png")
        )
        manager.loadUserRequest = {
            await recorder.record()
            return expected
        }

        await manager.restoreSession()

        #expect(await recorder.callCount == 1)
        #expect(manager.currentUser == expected)
    }

    @Test("loadUserRequest failure leaves currentUser unchanged so the UI can fall back to provider info")
    @MainActor
    func loadUserRequestFailureKeepsPriorCurrentUser() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.loadUserFail.\(UUID().uuidString)")!)
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

        manager.loadUserRequest = {
            throw URLError(.networkConnectionLost)
        }

        // Pin the catch-block log emission to a recorder so a regression that
        // silently swallowed the thrown error (without calling the seam) would
        // be caught in addition to the post-condition assertions below.
        let errorRecorder = LoadUserErrorRecorder()
        manager.loadUserErrorObserver = { error in
            await errorRecorder.record(error: error)
        }

        await manager.restoreSession()

        #expect(manager.currentUser == nil)
        guard case .authenticated = manager.state else {
            Issue.record("Expected authenticated state — /me failure must not unauthenticate the session")
            return
        }

        #expect(await errorRecorder.callCount == 1)
        let observed = await errorRecorder.lastError as? URLError
        #expect(observed?.code == .networkConnectionLost)
    }

    @Test("clearSession (sign out) resets currentUser back to nil")
    @MainActor
    func signOutResetsCurrentUser() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.clearUser.\(UUID().uuidString)")!)
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

        let user = AuthenticatedUser(
            displayName: "X",
            email: "x@example.com",
            avatarURL: nil
        )
        manager.loadUserRequest = { user }
        await manager.restoreSession()
        #expect(manager.currentUser == user)

        await manager.signOut()

        #expect(manager.currentUser == nil)
    }

    @Test("deleteAccount calls the server deletion before clearing all local session state")
    @MainActor
    func deleteAccountCallsServerDeleteBeforeClearingTokens() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.deleteAccount.\(UUID().uuidString)")!)
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

        let user = AuthenticatedUser(
            displayName: "X",
            email: "x@example.com",
            avatarURL: nil
        )
        manager.loadUserRequest = { user }
        await manager.restoreSession()
        #expect(manager.currentUser == user)

        let recorder = DeleteAccountRecorder()
        manager.deleteAccountRequest = { [authMiddleware] in
            let hadToken = await authMiddleware.hasAccessToken
            await recorder.record(hadAccessToken: hadToken)
        }

        try? await manager.deleteAccount()

        #expect(await recorder.callCount == 1)
        #expect(await recorder.observedAccessToken == true)
        #expect(manager.state == .signedOut(message: nil))
        #expect(manager.currentUser == nil)
        #expect(!tokenManager.isAuthenticated)
        #expect(!(await authMiddleware.hasAccessToken))
    }

    @Test("deleteAccount keeps the local session when the server deletion fails")
    @MainActor
    func deleteAccountKeepsLocalSessionWhenServerDeleteFails() async {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: "AuthManagerTests.deleteAccountFail.\(UUID().uuidString)")!)
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

        manager.deleteAccountRequest = {
            throw URLError(.badServerResponse)
        }

        do {
            try await manager.deleteAccount()
            Issue.record("Expected deleteAccount() to throw when the server deletion fails")
        } catch {
            #expect((error as? URLError)?.code == .badServerResponse)
        }

        guard case .authenticated = manager.state else {
            Issue.record("Expected deleteAccount() failure to keep the user authenticated")
            return
        }
        #expect(tokenManager.isAuthenticated)
        #expect(await authMiddleware.hasAccessToken)
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

private actor SignoutRecorder {
    var callCount = 0
    var observedAccessToken = false

    func record(hadAccessToken: Bool) {
        callCount += 1
        observedAccessToken = hadAccessToken
    }
}

private actor SignoutErrorRecorder {
    var callCount = 0
    var lastError: Error?

    func record(error: Error) {
        callCount += 1
        lastError = error
    }
}

private actor DeleteAccountRecorder {
    var callCount = 0
    var observedAccessToken = false

    func record(hadAccessToken: Bool) {
        callCount += 1
        observedAccessToken = hadAccessToken
    }
}

private actor LoadUserRecorder {
    var callCount = 0

    func record() {
        callCount += 1
    }
}

private actor LoadUserErrorRecorder {
    var callCount = 0
    var lastError: Error?

    func record(error: Error) {
        callCount += 1
        lastError = error
    }
}

private final class MockOAuthSessionRunner: OAuthSessionRunning {
    var callbackURL = URL(string: "laughtrack://auth/callback")!
    var error: Error?
    private(set) var lastStartURL: URL?
    private(set) var lastCallbackScheme: String?

    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        lastStartURL = startURL
        lastCallbackScheme = callbackScheme
        if let error {
            throw error
        }
        return callbackURL
    }
}
