import Testing
import Foundation
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

// Mirrors AppBootstrap's apiClient construction against a scripted ClientTransport so
// the TokenRefreshMiddleware rotation path can be asserted end-to-end: a 401 on a
// protected endpoint must drive a /auth/refresh call that (a) carries no Authorization
// header, (b) puts the keychain's refresh token in the request body, and (c) results in
// both AuthenticationMiddleware and the keychain holding the rotated pair after the
// original request is retried. Regression anchor for TASK-1725.
@Suite("TokenRefreshMiddleware AppBootstrap integration")
struct TokenRefreshMiddlewareIntegrationTests {

    @Test("401 on a protected call drives /auth/refresh and rotates tokens in authMiddleware and keychain")
    @MainActor
    func refreshOn401RotatesTokensInAuthMiddlewareAndKeychain() async throws {
        let secureStorage = IntegrationInMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "stale-access-token-\(UUID().uuidString)"
        let initialRefresh = "refresh-token-in-keychain-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let serverURL = URL(string: "https://test.example.com")!
        // Disable retries so the 401 surfaces directly to TokenRefreshMiddleware — the
        // default retry config doesn't retry 401 anyway, but this removes the dependency.
        let factory = APIClientFactory(
            serverURL: serverURL,
            retryConfiguration: .init(maxRetries: 0),
            secureStorage: secureStorage
        )

        let rotatedAccess = "rotated-access-token"
        let rotatedRefresh = "rotated-refresh-token"
        let transport = ScriptedTransport()
        await transport.seed([
            .response(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
            .response(
                status: .ok,
                bodyJSON: """
                {"accessToken":"\(rotatedAccess)","refreshToken":"\(rotatedRefresh)","expiresIn":900}
                """
            ),
            .response(status: .ok, bodyJSON: #"{"data":[]}"#),
        ])

        // refreshClient intentionally omits factory.authMiddleware — see AppBootstrap.
        let refreshClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        // This test exercises TokenRefreshMiddleware's rotation contract, not the
        // signed-out notification plumbing, so the refresh closure's unauthorized
        // handler and UnauthorizedResponseMiddleware's callback are both no-ops.
        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id,
            refreshHandler: makeProductionStyleRefreshClosure(
                tokenManager: tokenManager,
                refreshClient: refreshClient,
                unauthorizedHandler: { }
            )
        )

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        _ = try await apiClient.getFavorites()

        let recorded = await transport.recordedRequests
        #expect(recorded.count == 3)

        let firstAttempt = try #require(recorded[safe: 0])
        let refreshRequest = try #require(recorded[safe: 1])
        let retriedAttempt = try #require(recorded[safe: 2])

        #expect(firstAttempt.operationID == "getFavorites")
        #expect(refreshRequest.operationID == Operations.RefreshToken.id)
        #expect(retriedAttempt.operationID == "getFavorites")

        // Criterion 1: /auth/refresh must not carry the expired access token. This is
        // the invariant TASK-1725 restored by dropping authMiddleware from refreshClient.
        #expect(refreshRequest.headers[.authorization] == nil)

        // The original 401 was signed with the stale access token; the retry rides the
        // rotated token. Verifying both protects the "retry picks up the new token"
        // leg of the rotation contract.
        #expect(firstAttempt.headers[.authorization] == "Bearer \(initialAccess)")
        #expect(retriedAttempt.headers[.authorization] == "Bearer \(rotatedAccess)")

        // Criterion 2: decoded JSON body contains the refresh token from keychain.
        let bodyData = try #require(refreshRequest.bodyData)
        let decoded = try JSONDecoder().decode(
            Components.Schemas.RefreshTokenRequest.self,
            from: bodyData
        )
        #expect(decoded.refreshToken == initialRefresh)

        // Criterion 3: authMiddleware and keychain both hold the rotated pair.
        #expect(await factory.authMiddleware.getAccessToken() == rotatedAccess)
        #expect(tokenManager.retrieveAccessToken() == rotatedAccess)
        #expect(tokenManager.retrieveRefreshToken() == rotatedRefresh)
    }

    // A successful 401 -> refresh -> 200 cycle must NOT drive
    // UnauthorizedResponseMiddleware.onUnauthorized, because that callback clears the
    // keychain and flips AuthManager to .signedOut. Regression anchor for TASK-1755:
    // prior to the reorder, TokenRefreshMiddleware sat outside UnauthorizedResponseMiddleware,
    // so the 401 reached UnauthorizedResponseMiddleware first and signed the user out even
    // though the retry ultimately succeeded.
    @Test("401 -> refresh -> 200 leaves AuthManager authenticated and keychain populated")
    @MainActor
    func successfulRefreshDoesNotTriggerUnauthorizedCallback() async throws {
        let secureStorage = IntegrationInMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "stale-access-token-\(UUID().uuidString)"
        let initialRefresh = "refresh-token-in-keychain-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let suiteName = "TokenRefreshMiddlewareIntegrationTests.\(UUID().uuidString)"
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: suiteName)!)

        let serverURL = URL(string: "https://test.example.com")!
        let factory = APIClientFactory(
            serverURL: serverURL,
            retryConfiguration: .init(maxRetries: 0),
            secureStorage: secureStorage
        )

        let authManager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: StubOAuthSessionRunner()
        )
        await authManager.restoreSession()

        // Precondition: restoreSession flipped us to .authenticated.
        guard case .authenticated = authManager.state else {
            Issue.record("Expected AuthManager to be .authenticated after restoreSession, got \(authManager.state)")
            return
        }

        let rotatedAccess = "rotated-access-token"
        let rotatedRefresh = "rotated-refresh-token"
        let transport = ScriptedTransport()
        await transport.seed([
            .response(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
            .response(
                status: .ok,
                bodyJSON: """
                {"accessToken":"\(rotatedAccess)","refreshToken":"\(rotatedRefresh)","expiresIn":900}
                """
            ),
            .response(status: .ok, bodyJSON: #"{"data":[]}"#),
        ])

        let refreshClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id,
            refreshHandler: makeProductionStyleRefreshClosure(
                tokenManager: tokenManager,
                refreshClient: refreshClient,
                unauthorizedHandler: { [authManager] in
                    await authManager.handleUnauthorizedResponse()
                }
            )
        )

        // The real production callback — this is exactly what AppBootstrap wires up.
        // The whole point of this test is that it must NOT fire when refresh recovers.
        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { [authManager] in
            await authManager.handleUnauthorizedResponse()
        }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        _ = try await apiClient.getFavorites()

        // Core assertion: AuthManager stayed .authenticated through the refresh cycle.
        guard case .authenticated = authManager.state else {
            Issue.record("Expected AuthManager to stay .authenticated after 401 -> refresh -> 200, got \(authManager.state)")
            return
        }
        #expect(tokenManager.isAuthenticated)
        #expect(tokenManager.retrieveAccessToken() == rotatedAccess)
        #expect(tokenManager.retrieveRefreshToken() == rotatedRefresh)
        #expect(await factory.authMiddleware.getAccessToken() == rotatedAccess)

        // Sanity check: all three transport hops were observed (401, refresh, retry).
        let recorded = await transport.recordedRequests
        #expect(recorded.count == 3)
    }

    // Edge case 1 of TASK-1754: when /auth/refresh itself returns 401 (refresh token
    // expired or revoked server-side), the closure's response check fails, the closure
    // calls handleUnauthorizedResponse, and throws. TRM must NOT loop — it must propagate
    // the error and never retry the original protected call. The transport sees exactly
    // two hops: the original 401 and the refresh attempt. Anything more would mean TRM
    // re-entered after a refresh-endpoint 401, defeating the operationID loop guard.
    @Test("401 from /auth/refresh signs the user out and does not retry the original request")
    @MainActor
    func refreshEndpoint401DoesNotLoopAndSignsOut() async throws {
        let secureStorage = IntegrationInMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "stale-access-token-\(UUID().uuidString)"
        let initialRefresh = "expired-refresh-token-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let suiteName = "TokenRefreshMiddlewareIntegrationTests.\(UUID().uuidString)"
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: suiteName)!)

        let serverURL = URL(string: "https://test.example.com")!
        let factory = APIClientFactory(
            serverURL: serverURL,
            retryConfiguration: .init(maxRetries: 0),
            secureStorage: secureStorage
        )

        let authManager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: StubOAuthSessionRunner()
        )
        await authManager.restoreSession()

        guard case .authenticated = authManager.state else {
            Issue.record("Expected AuthManager to be .authenticated after restoreSession, got \(authManager.state)")
            return
        }

        let transport = ScriptedTransport()
        await transport.seed([
            .response(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
            .response(status: .unauthorized, bodyJSON: #"{"error":"Refresh token expired."}"#),
        ])

        let refreshClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id,
            refreshHandler: makeProductionStyleRefreshClosure(
                tokenManager: tokenManager,
                refreshClient: refreshClient,
                unauthorizedHandler: { [authManager] in
                    await authManager.handleUnauthorizedResponse()
                }
            )
        )

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { [authManager] in
            await authManager.handleUnauthorizedResponse()
        }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        do {
            _ = try await apiClient.getFavorites()
            Issue.record("Expected getFavorites to throw after /auth/refresh returned 401")
        } catch let error as ClientError {
            // OpenAPIRuntime wraps any middleware throw in ClientError; the closure's
            // URLError is what the integration contract guarantees underneath.
            #expect(error.underlyingError is URLError)
        } catch {
            Issue.record("Expected ClientError wrapping URLError, got \(type(of: error)): \(error)")
        }

        let recorded = await transport.recordedRequests
        // Two hops, no third. A third hop would mean TRM re-entered refresh after the
        // refresh endpoint returned 401 — that's exactly the loop the operationID guard
        // and the closure's throw-on-non-200 path are designed to prevent.
        #expect(recorded.count == 2)
        #expect(recorded[safe: 0]?.operationID == "getFavorites")
        #expect(recorded[safe: 1]?.operationID == Operations.RefreshToken.id)

        guard case .signedOut = authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after refresh-endpoint 401, got \(authManager.state)")
            return
        }
        #expect(tokenManager.isAuthenticated == false)
        #expect(tokenManager.retrieveAccessToken() == nil)
        #expect(tokenManager.retrieveRefreshToken() == nil)
        #expect(await factory.authMiddleware.getAccessToken() == nil)
    }

    // Edge case 2 of TASK-1754: when the refresh closure throws (network error before a
    // response, or any other failure that escapes before the closure mutates state), TRM
    // must propagate the error and leave the rotation state untouched — no
    // setTokens(...) call on authMiddleware, and the keychain still holds the originals.
    // This is the invariant that "the caller surfaces the original 401 or thrown error
    // without corrupting keychain state": TRM's contribution is to not partially rotate
    // when the closure aborts.
    @Test("Refresh closure throws — TRM propagates the error and does not mutate token state")
    @MainActor
    func refreshClosureThrowingPreservesTokenState() async throws {
        let secureStorage = IntegrationInMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "stale-access-token-\(UUID().uuidString)"
        let initialRefresh = "refresh-token-in-keychain-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let serverURL = URL(string: "https://test.example.com")!
        let factory = APIClientFactory(
            serverURL: serverURL,
            retryConfiguration: .init(maxRetries: 0),
            secureStorage: secureStorage
        )

        let transport = ScriptedTransport()
        await transport.seed([
            .response(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
        ])

        struct SimulatedRefreshFailure: Error {}

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id
        ) { _ in
            // Stand-in for any closure-internal failure that escapes before the closure
            // touches authMiddleware or the keychain — e.g. URLSession-level network
            // error from refreshClient, or a JSON decode error before storeTokens.
            throw SimulatedRefreshFailure()
        }

        // No-op unauthorized callback: this test isolates TRM's behavior on a closure
        // throw, not the production sign-out plumbing.
        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        do {
            _ = try await apiClient.getFavorites()
            Issue.record("Expected getFavorites to throw after refresh closure failed")
        } catch let error as ClientError {
            #expect(error.underlyingError is SimulatedRefreshFailure)
        } catch {
            Issue.record("Expected ClientError wrapping SimulatedRefreshFailure, got \(type(of: error)): \(error)")
        }

        let recorded = await transport.recordedRequests
        // Only the original protected call was recorded — TRM aborted before retrying
        // and the closure never reached refreshClient.
        #expect(recorded.count == 1)
        #expect(recorded[safe: 0]?.operationID == "getFavorites")

        // Core invariant: TRM never called authMiddleware.setTokens, so the in-memory
        // and keychain copies still hold the pre-refresh pair.
        #expect(await factory.authMiddleware.getAccessToken() == initialAccess)
        #expect(tokenManager.retrieveAccessToken() == initialAccess)
        #expect(tokenManager.retrieveRefreshToken() == initialRefresh)
    }

    // Edge case 3 of TASK-1754: the refresh token entry is missing from the keychain
    // when a 401 fires (keychain corruption, OS-level wipe, or any path where the
    // access token survived but the refresh did not). The closure's
    // retrieveRefreshToken() returns nil, so it must short-circuit — no /auth/refresh
    // call is made, the user is signed out, and TRM propagates the error.
    @Test("Missing refresh token in keychain on 401 signs the user out without calling /auth/refresh")
    @MainActor
    func missingRefreshTokenSignsOutWithoutHittingRefreshEndpoint() async throws {
        let secureStorage = IntegrationInMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "stale-access-token-\(UUID().uuidString)"
        let initialRefresh = "refresh-token-in-keychain-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let suiteName = "TokenRefreshMiddlewareIntegrationTests.\(UUID().uuidString)"
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: suiteName)!)

        let serverURL = URL(string: "https://test.example.com")!
        let factory = APIClientFactory(
            serverURL: serverURL,
            retryConfiguration: .init(maxRetries: 0),
            secureStorage: secureStorage
        )

        let authManager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: StubOAuthSessionRunner()
        )
        await authManager.restoreSession()

        guard case .authenticated = authManager.state else {
            Issue.record("Expected AuthManager to be .authenticated after restoreSession, got \(authManager.state)")
            return
        }

        // Drop just the refresh token after AuthManager has already entered .authenticated.
        // restoreSession would have force-cleared the access token if the refresh entry
        // were missing at restore time, so this models a refresh entry that disappeared
        // mid-session (corruption, external wipe).
        try secureStorage.delete(forKey: AuthStorageKeys.refreshToken)
        #expect(tokenManager.retrieveRefreshToken() == nil)

        let transport = ScriptedTransport()
        await transport.seed([
            .response(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
        ])

        let refreshClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id,
            refreshHandler: makeProductionStyleRefreshClosure(
                tokenManager: tokenManager,
                refreshClient: refreshClient,
                unauthorizedHandler: { [authManager] in
                    await authManager.handleUnauthorizedResponse()
                }
            )
        )

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { [authManager] in
            await authManager.handleUnauthorizedResponse()
        }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        do {
            _ = try await apiClient.getFavorites()
            Issue.record("Expected getFavorites to throw when no refresh token is present")
        } catch let error as ClientError {
            #expect(error.underlyingError is URLError)
        } catch {
            Issue.record("Expected ClientError wrapping URLError, got \(type(of: error)): \(error)")
        }

        let recorded = await transport.recordedRequests
        // Only the protected call was attempted; the closure short-circuited before
        // reaching refreshClient, so /auth/refresh is never on the wire.
        #expect(recorded.count == 1)
        #expect(recorded[safe: 0]?.operationID == "getFavorites")

        guard case .signedOut = authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after missing-refresh 401, got \(authManager.state)")
            return
        }
        #expect(tokenManager.isAuthenticated == false)
        #expect(tokenManager.retrieveAccessToken() == nil)
        #expect(tokenManager.retrieveRefreshToken() == nil)
        #expect(await factory.authMiddleware.getAccessToken() == nil)
    }
}

// Shared fixtures (ScriptedTransport, ScriptedResponse, RecordedRequest,
// IntegrationInMemorySecureStorage, StubOAuthSessionRunner, and the
// production-style refresh closure) live in MiddlewareIntegrationTestSupport.swift.

// Kept fileprivate (rather than module-internal in the support file) so the
// generic Array helper doesn't bleed into the rest of the test target —
// TokenRefreshMiddlewareIntegrationTests is the only file that uses it.
fileprivate extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
