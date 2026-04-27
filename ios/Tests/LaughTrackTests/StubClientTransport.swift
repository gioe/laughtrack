import Foundation
import HTTPTypes
import OpenAPIRuntime

/// In-process `ClientTransport` stub for tests. Lets each test inject a
/// deterministic response without spinning up a real network. Each test
/// instantiates its own transport, so the handler is per-instance and never
/// shared across tests.
///
/// Three constructors cover the common cases:
///   - `init()` — no handler set; `send` throws `URLError(.unknown)` until
///     `setHandler(_:)` is called. Use this when each test wants to inject a
///     different response, the way `APIZipLocationResolverTests` does.
///   - `alwaysSucceeds()` — handler returns `200 OK` with no body. Use when
///     the test exercises a code path that *constructs* a `Client` but never
///     actually issues a request (e.g. service-registration sanity tests).
///   - `alwaysFails()` — handler throws `URLError(.notConnectedToInternet)`.
///     Use when the test exercises offline / failure paths or only needs a
///     `Client` instance to satisfy a constructor signature.
///
/// All three modes capture every request through `capturedRequests`, so a
/// test that wants to assert on method/path/baseURL/operationID can do so
/// regardless of which factory built it.
final class StubClientTransport: ClientTransport, @unchecked Sendable {
    typealias Handler = @Sendable (HTTPRequest, HTTPBody?, URL, String) async throws -> (HTTPResponse, HTTPBody?)

    struct CapturedRequest {
        let method: HTTPRequest.Method
        let path: String?
        let baseURL: URL
        let operationID: String
    }

    private let lock = NSLock()
    private var handler: Handler?
    private var requests: [CapturedRequest] = []

    init(handler: Handler? = nil) {
        self.handler = handler
    }

    static func alwaysSucceeds() -> StubClientTransport {
        StubClientTransport { _, _, _, _ in
            (HTTPResponse(status: .ok), nil)
        }
    }

    static func alwaysFails() -> StubClientTransport {
        StubClientTransport { _, _, _, _ in
            throw URLError(.notConnectedToInternet)
        }
    }

    func setHandler(_ handler: @escaping Handler) {
        lock.withLock {
            self.handler = handler
            self.requests = []
        }
    }

    var capturedRequests: [CapturedRequest] {
        lock.withLock { requests }
    }

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let captured: Handler? = lock.withLock {
            requests.append(
                CapturedRequest(
                    method: request.method,
                    path: request.path,
                    baseURL: baseURL,
                    operationID: operationID
                )
            )
            return handler
        }

        guard let captured else {
            throw URLError(.unknown)
        }
        return try await captured(request, body, baseURL, operationID)
    }
}
