import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
@testable import LaughTrackCore

private let baseURL = URL(string: "https://test.example.com")!

@Suite("APIZipLocationResolver")
struct APIZipLocationResolverTests {

    @Test("200 with valid payload decodes city and state into ResolvedNearbyLocation")
    @MainActor
    func successDecodesCityAndState() async throws {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 200, body: #"{"city":"Chicago","state":"IL"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))
        let result = try await resolver.resolveLocation(forZip: "60614")

        #expect(result.zipCode == "60614")
        #expect(result.city == "Chicago")
        #expect(result.state == "IL")
    }

    @Test("200 with malformed JSON throws lookupFailed")
    @MainActor
    func malformedJSONFailsLookup() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 200, body: "{not json")
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))

        await #expect(throws: ZipLocationLookupError.lookupFailed) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("400 response throws invalidZip")
    @MainActor
    func status400ThrowsInvalidZip() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 400, body: #"{"error":"bad zip"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))

        await #expect(throws: ZipLocationLookupError.invalidZip) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("404 response throws unknownZip")
    @MainActor
    func status404ThrowsUnknownZip() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 404, body: #"{"error":"unknown"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))

        await #expect(throws: ZipLocationLookupError.unknownZip) {
            _ = try await resolver.resolveLocation(forZip: "99999")
        }
    }

    @Test("undocumented response (500) throws lookupFailed")
    @MainActor
    func nonSuccessStatusThrowsLookupFailed() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 500, body: #"{"error":"server error"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))

        await #expect(throws: ZipLocationLookupError.lookupFailed) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("429 rate-limit response throws lookupFailed")
    @MainActor
    func rateLimitedStatusThrowsLookupFailed() async {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 429, body: #"{"error":"rate limited"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))

        await #expect(throws: ZipLocationLookupError.lookupFailed) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("Request URL is composed as <baseURL>/api/v1/zip-lookup?zip=<zip>")
    @MainActor
    func requestURLComposition() async throws {
        let transport = StubClientTransport()
        transport.setHandler { _, _, _, _ in
            jsonResponse(status: 200, body: #"{"city":"Chicago","state":"IL"}"#)
        }

        let resolver = APIZipLocationResolver(apiClient: makeClient(transport: transport))
        _ = try await resolver.resolveLocation(forZip: "10012")

        let captured = transport.capturedRequests
        #expect(captured.count == 1)
        let first = try #require(captured.first)
        #expect(first.method == .get)
        let path = try #require(first.path)
        #expect(path == "/api/v1/zip-lookup?zip=10012")
        #expect(first.baseURL == baseURL)
    }
}

@MainActor
private func makeClient(transport: any ClientTransport) -> Client {
    Client(
        serverURL: baseURL,
        transport: transport,
        middlewares: [APIVersionPathMiddleware()]
    )
}

private func jsonResponse(status: Int, body: String) -> (HTTPResponse, HTTPBody?) {
    var response = HTTPResponse(status: .init(code: status))
    response.headerFields[.contentType] = "application/json"
    return (response, HTTPBody(body))
}

/// In-process `ClientTransport` stub that lets each test inject a deterministic
/// response without spinning up a real network. Each test instantiates its own
/// transport, so the handler is per-instance and never shared across tests.
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
