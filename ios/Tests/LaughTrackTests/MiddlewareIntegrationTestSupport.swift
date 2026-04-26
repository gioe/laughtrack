import Foundation
import HTTPTypes
import OpenAPIRuntime
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

// Shared harness for middleware-integration tests. Both
// TokenRefreshMiddlewareIntegrationTests and AuthManagerSignOutIntegrationTests
// stand up a real Client + AppBootstrap-style middleware chain against a scripted
// ClientTransport; the fixtures below were duplicated verbatim across both files
// before, with the ScriptedResponse shape having already diverged (struct vs.
// enum). This file is the single source of truth — extend the enum here when
// future tests need a new transport behavior rather than re-defining a parallel
// shape per file.

// MARK: - Scripted Transport

struct RecordedRequest: Sendable {
    let method: HTTPRequest.Method
    let path: String?
    let headers: HTTPFields
    let operationID: String
    let bodyData: Data?
}

enum ScriptedResponse: Sendable {
    case response(status: HTTPResponse.Status, bodyJSON: String?)
    case transportError(URLError)
}

actor ScriptedTransportState {
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

final class ScriptedTransport: ClientTransport, @unchecked Sendable {
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

final class StubOAuthSessionRunner: OAuthSessionRunning {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        URL(string: "laughtrack://auth/callback")!
    }
}

// Named with the `Integration` prefix to avoid an `invalid redeclaration` clash
// with the file-private `InMemorySecureStorage` types that AuthManagerTests.swift
// and HostedViewTestSupport.swift each declare locally — Swift treats a module-
// internal type with the same name as a redeclaration of those private siblings.
// Future consolidation across all three test files would lift those private
// copies into this fixture; that's a strictly broader refactor than this task.
final class IntegrationInMemorySecureStorage: SecureStorageProtocol {
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

// MARK: - Refresh Closure Helper

/// Builds the AppBootstrap-style refresh closure used by every middleware-integration
/// test that exercises the real `TokenRefreshMiddleware`. Mirrors AppBootstrap.swift's
/// closure: read the keychain's refresh token, POST it to /auth/refresh via a
/// dedicated client (no AuthenticationMiddleware), persist the rotated pair, and
/// return them so TRM updates `AuthenticationMiddleware`. On any failure path it
/// invokes `unauthorizedHandler` (the production wiring calls
/// `authManager.handleUnauthorizedResponse()`) before throwing.
///
/// Pass `unauthorizedHandler: { }` for tests that want the production-style refresh
/// flow but intentionally isolate TRM from the sign-out plumbing — e.g. when the
/// test only exercises the happy path and never trips a failure guard.
func makeProductionStyleRefreshClosure(
    tokenManager: AuthTokenManager,
    refreshClient: Client,
    unauthorizedHandler: @escaping @Sendable () async -> Void
) -> TokenRefreshMiddleware.RefreshHandler {
    return { _ in
        let refreshToken = await MainActor.run { tokenManager.retrieveRefreshToken() }
        guard let refreshToken else {
            await unauthorizedHandler()
            throw URLError(.userAuthenticationRequired)
        }
        let response = try await refreshClient.refreshToken(
            body: .json(.init(refreshToken: refreshToken))
        )
        guard case .ok(let ok) = response, case .json(let body) = ok.body else {
            await unauthorizedHandler()
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
}

