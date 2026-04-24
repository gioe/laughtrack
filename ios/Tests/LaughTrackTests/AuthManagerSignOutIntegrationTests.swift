import Testing
import Foundation
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

// Mirrors AppBootstrap's apiClient construction against a scripted ClientTransport so
// the AuthManager.signOut() path can be asserted end-to-end: signOut() must
// (a) issue POST /api/v1/auth/signout with the stored access token as a Bearer
// credential, (b) drain local state to .signedOut even when the server call fails,
// and (c) be distinct from handleUnauthorizedResponse(), which clears state without
// hitting the revocation endpoint. Regression anchor for TASK-1748 / TASK-1750.
@Suite("AuthManager.signOut AppBootstrap integration")
struct AuthManagerSignOutIntegrationTests {

    @Test("signOut() issues POST /auth/signout carrying the stored access token and drains to signedOut")
    @MainActor
    func signOutHitsSignoutEndpointWithBearerAndClearsState() async throws {
        let harness = try await AuthSignOutHarness.make()

        await harness.transport.seed([.response(status: .ok, bodyJSON: #"{"revoked":1}"#)])

        await harness.authManager.signOut()

        let recorded = await harness.transport.recordedRequests
        #expect(recorded.count == 1)

        let request = try #require(recorded.first)
        #expect(request.operationID == "signout")
        #expect(request.method == .post)
        #expect(request.path == "/api/v1/auth/signout")

        // Criterion 2: the Bearer header must match the access token that was in
        // the keychain at the moment signOut() fired — proof that the real
        // AuthenticationMiddleware signed the request, not a closure mock.
        #expect(request.headers[.authorization] == "Bearer \(harness.initialAccess)")

        // Local state drained: keychain empty, authMiddleware empty, state .signedOut.
        guard case .signedOut = harness.authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after signOut(), got \(harness.authManager.state)")
            return
        }
        #expect(harness.tokenManager.retrieveAccessToken() == nil)
        #expect(harness.tokenManager.retrieveRefreshToken() == nil)
        #expect(await harness.factory.authMiddleware.getAccessToken() == nil)
    }

    @Test("signOut() drains state to signedOut even when the transport throws")
    @MainActor
    func signOutClearsLocalStateEvenWhenServerCallFails() async throws {
        let harness = try await AuthSignOutHarness.make()

        await harness.transport.seed([.transportError(URLError(.notConnectedToInternet))])

        await harness.authManager.signOut()

        // The server call still went out — it just failed in flight. Verifying the
        // request was recorded protects the "attempt revocation while we still have
        // a valid Bearer" contract in AuthManager.signOut().
        let recorded = await harness.transport.recordedRequests
        #expect(recorded.count == 1)

        let request = try #require(recorded.first)
        #expect(request.operationID == "signout")
        #expect(request.headers[.authorization] == "Bearer \(harness.initialAccess)")

        // Core assertion: local sign-out must complete regardless of the server-side
        // outcome — the user expects to end up signed out no matter what.
        guard case .signedOut = harness.authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after failed signOut(), got \(harness.authManager.state)")
            return
        }
        #expect(harness.tokenManager.retrieveAccessToken() == nil)
        #expect(harness.tokenManager.retrieveRefreshToken() == nil)
        #expect(await harness.factory.authMiddleware.getAccessToken() == nil)
    }

    @Test("signOut() drains state to signedOut when the server returns 500")
    @MainActor
    func signOutClearsLocalStateEvenWhenServerReturns500() async throws {
        let harness = try await AuthSignOutHarness.make()

        // Covers the 500-specific path named in criterion 5853: the generated
        // client decodes the response envelope and produces an .undocumented
        // Output case (POST /auth/signout has no 5xx branch in the OpenAPI spec),
        // which differs from the at-transport throw exercised by the sibling test.
        await harness.transport.seed([
            .response(status: .internalServerError, bodyJSON: #"{"error":"Server error"}"#)
        ])

        await harness.authManager.signOut()

        let recorded = await harness.transport.recordedRequests
        #expect(recorded.count == 1)

        let request = try #require(recorded.first)
        #expect(request.operationID == "signout")
        #expect(request.headers[.authorization] == "Bearer \(harness.initialAccess)")

        guard case .signedOut = harness.authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after 500 signOut(), got \(harness.authManager.state)")
            return
        }
        #expect(harness.tokenManager.retrieveAccessToken() == nil)
        #expect(harness.tokenManager.retrieveRefreshToken() == nil)
        #expect(await harness.factory.authMiddleware.getAccessToken() == nil)
    }

    @Test("handleUnauthorizedResponse() clears state without issuing POST /auth/signout")
    @MainActor
    func handleUnauthorizedResponseDoesNotHitSignoutEndpoint() async throws {
        let harness = try await AuthSignOutHarness.make()

        // handleUnauthorizedResponse() short-circuits before touching the apiClient
        // at all — it only calls clearSession(). Seeding nothing and asserting
        // recorded.isEmpty below proves that no /auth/signout request left the
        // client, which is the invariant the path separation exists to protect.
        await harness.transport.seed([])

        await harness.authManager.handleUnauthorizedResponse()

        let recorded = await harness.transport.recordedRequests
        #expect(recorded.isEmpty)

        guard case .signedOut = harness.authManager.state else {
            Issue.record("Expected AuthManager to be .signedOut after handleUnauthorizedResponse(), got \(harness.authManager.state)")
            return
        }
        #expect(harness.tokenManager.retrieveAccessToken() == nil)
        #expect(harness.tokenManager.retrieveRefreshToken() == nil)
    }
}

// MARK: - Harness

@MainActor
private struct AuthSignOutHarness {
    let authManager: AuthManager
    let tokenManager: AuthTokenManager
    let factory: APIClientFactory
    let transport: ScriptedTransport
    let initialAccess: String
    let initialRefresh: String

    /// Wires together the same AuthManager + apiClient stack that AppBootstrap produces,
    /// routed through a scripted transport, with a test session already restored to
    /// `.authenticated`. The signoutRequest binding exactly mirrors AppBootstrap.swift:114.
    static func make() async throws -> AuthSignOutHarness {
        let secureStorage = InMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let initialAccess = "access-token-\(UUID().uuidString)"
        let initialRefresh = "refresh-token-\(UUID().uuidString)"
        try tokenManager.storeTokens(accessToken: initialAccess, refreshToken: initialRefresh)

        let suiteName = "AuthManagerSignOutIntegrationTests.\(UUID().uuidString)"
        let appStateStorage = AppStateStorage(userDefaults: UserDefaults(suiteName: suiteName)!)

        let serverURL = URL(string: "https://test.example.com")!
        // maxRetries: 0 is belt-and-suspenders — RetryMiddleware's default policy
        // already skips POST and skips thrown transport errors, so a signout call
        // would not retry. Pinning it here keeps the recorded-request count stable
        // if RetryMiddleware's defaults ever broaden.
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
            throw HarnessSetupError(
                "Expected AuthManager to be .authenticated after restoreSession, got \(authManager.state)"
            )
        }

        let transport = ScriptedTransport()

        // refreshClient mirrors AppBootstrap: no authMiddleware (the /auth/refresh
        // contract carries the refresh token in the body and must not sign the
        // request with the potentially-stale access token).
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
            refreshEndpointOperationID: Operations.RefreshToken.id
        ) { _ in
            let refreshToken = await MainActor.run { tokenManager.retrieveRefreshToken() }
            guard let refreshToken else {
                await authManager.handleUnauthorizedResponse()
                throw URLError(.userAuthenticationRequired)
            }
            let response = try await refreshClient.refreshToken(
                body: .json(.init(refreshToken: refreshToken))
            )
            guard case .ok(let ok) = response, case .json(let body) = ok.body else {
                await authManager.handleUnauthorizedResponse()
                throw URLError(.userAuthenticationRequired)
            }
            try? await MainActor.run {
                try tokenManager.storeTokens(
                    accessToken: body.accessToken,
                    refreshToken: body.refreshToken
                )
            }
            return TokenRefreshMiddleware.Tokens(
                accessToken: body.accessToken,
                refreshToken: body.refreshToken
            )
        }

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

        authManager.signoutRequest = { [apiClient] in
            _ = try await apiClient.signout()
        }

        return AuthSignOutHarness(
            authManager: authManager,
            tokenManager: tokenManager,
            factory: factory,
            transport: transport,
            initialAccess: initialAccess,
            initialRefresh: initialRefresh
        )
    }
}

private struct HarnessSetupError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

// MARK: - Scripted Transport

private struct RecordedRequest: Sendable {
    let method: HTTPRequest.Method
    let path: String?
    let headers: HTTPFields
    let operationID: String
    let bodyData: Data?
}

private enum ScriptedResponse: Sendable {
    case response(status: HTTPResponse.Status, bodyJSON: String?)
    case transportError(URLError)
}

private actor ScriptedTransportState {
    private var script: [ScriptedResponse] = []
    private(set) var recordedRequests: [RecordedRequest] = []

    func seed(_ script: [ScriptedResponse]) {
        self.script = script
        self.recordedRequests = []
    }

    func handle(_ request: RecordedRequest) -> ScriptedResponse? {
        recordedRequests.append(request)
        guard !script.isEmpty else { return nil }
        return script.removeFirst()
    }
}

private final class ScriptedTransport: ClientTransport, @unchecked Sendable {
    private let state = ScriptedTransportState()

    var recordedRequests: [RecordedRequest] {
        get async { await state.recordedRequests }
    }

    func seed(_ script: [ScriptedResponse]) async {
        await state.seed(script)
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        var collected: Data?
        if let body {
            collected = try await Data(collecting: body, upTo: 1_048_576)
        }
        let recorded = RecordedRequest(
            method: request.method,
            path: request.path,
            headers: request.headerFields,
            operationID: operationID,
            bodyData: collected
        )
        guard let scripted = await state.handle(recorded) else {
            throw URLError(.badServerResponse)
        }
        switch scripted {
        case .transportError(let error):
            throw error
        case .response(let status, let bodyJSON):
            var response = HTTPResponse(status: status)
            let responseBody: HTTPBody?
            if let json = bodyJSON {
                response.headerFields[.contentType] = "application/json"
                responseBody = HTTPBody(Data(json.utf8))
            } else {
                responseBody = nil
            }
            return (response, responseBody)
        }
    }
}

// MARK: - Test Fixtures

private final class StubOAuthSessionRunner: OAuthSessionRunning {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        URL(string: "laughtrack://auth/callback")!
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
