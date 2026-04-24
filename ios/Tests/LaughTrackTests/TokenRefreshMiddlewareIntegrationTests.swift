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
        let secureStorage = InMemorySecureStorage()
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
            ScriptedResponse(status: .unauthorized, bodyJSON: #"{"error":"Session expired."}"#),
            ScriptedResponse(
                status: .ok,
                bodyJSON: """
                {"accessToken":"\(rotatedAccess)","refreshToken":"\(rotatedRefresh)","expiresIn":900}
                """
            ),
            ScriptedResponse(status: .ok, bodyJSON: #"{"data":[]}"#),
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

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id
        ) { _ in
            let refreshToken = await MainActor.run { tokenManager.retrieveRefreshToken() }
            guard let refreshToken else {
                throw URLError(.userAuthenticationRequired)
            }
            let response = try await refreshClient.refreshToken(
                body: .json(.init(refreshToken: refreshToken))
            )
            guard case .ok(let ok) = response, case .json(let body) = ok.body else {
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

        // This test exercises TokenRefreshMiddleware's rotation contract, not the
        // signed-out notification plumbing, so the unauthorized callback is a no-op.
        let unauthorizedMiddleware = UnauthorizedResponseMiddleware { }

        let apiClient = Client(
            serverURL: serverURL,
            transport: transport,
            middlewares: [
                APIVersionPathMiddleware(),
                tokenRefreshMiddleware,
                unauthorizedMiddleware,
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
}

// MARK: - Scripted Transport

private struct RecordedRequest: Sendable {
    let method: HTTPRequest.Method
    let path: String?
    let headers: HTTPFields
    let operationID: String
    let bodyData: Data?
}

private struct ScriptedResponse: Sendable {
    let status: HTTPResponse.Status
    let bodyJSON: String?
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
        var response = HTTPResponse(status: scripted.status)
        let responseBody: HTTPBody?
        if let json = scripted.bodyJSON {
            response.headerFields[.contentType] = "application/json"
            responseBody = HTTPBody(Data(json.utf8))
        } else {
            responseBody = nil
        }
        return (response, responseBody)
    }
}

// MARK: - Test Fixtures

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

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
