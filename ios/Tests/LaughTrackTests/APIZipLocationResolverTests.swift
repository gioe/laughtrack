import Foundation
import Testing
@testable import LaughTrackCore

@Suite("APIZipLocationResolver", .serialized)
struct APIZipLocationResolverTests {
    private static let baseURL = URL(string: "https://test.example.com")!

    @Test("200 with valid payload decodes city and state into ResolvedNearbyLocation")
    @MainActor
    func successDecodesCityAndState() async throws {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 200), Data(#"{"city":"Chicago","state":"IL"}"#.utf8))
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())
        let result = try await resolver.resolveLocation(forZip: "60614")

        #expect(result.zipCode == "60614")
        #expect(result.city == "Chicago")
        #expect(result.state == "IL")
    }

    @Test("200 with malformed JSON throws lookupFailed")
    @MainActor
    func malformedJSONFailsLookup() async {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 200), Data("{not json".utf8))
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())

        await #expect(throws: ZipLocationLookupError.lookupFailed) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("400 response throws invalidZip")
    @MainActor
    func status400ThrowsInvalidZip() async {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 400), Data())
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())

        await #expect(throws: ZipLocationLookupError.invalidZip) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("404 response throws unknownZip")
    @MainActor
    func status404ThrowsUnknownZip() async {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 404), Data())
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())

        await #expect(throws: ZipLocationLookupError.unknownZip) {
            _ = try await resolver.resolveLocation(forZip: "99999")
        }
    }

    @Test("non-2xx response (500) throws lookupFailed")
    @MainActor
    func nonSuccessStatusThrowsLookupFailed() async {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 500), Data())
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())

        await #expect(throws: ZipLocationLookupError.lookupFailed) {
            _ = try await resolver.resolveLocation(forZip: "60614")
        }
    }

    @Test("Request URL is composed as <baseURL>/api/v1/zip-lookup?zip=<zip>")
    @MainActor
    func requestURLComposition() async throws {
        StubURLProtocol.setHandler { request in
            (response(for: request, status: 200), Data(#"{"city":"Chicago","state":"IL"}"#.utf8))
        }
        defer { StubURLProtocol.reset() }

        let resolver = APIZipLocationResolver(baseURL: Self.baseURL, session: makeStubbedSession())
        _ = try await resolver.resolveLocation(forZip: "10012")

        let captured = StubURLProtocol.capturedRequests
        #expect(captured.count == 1)
        #expect(captured.first?.url?.absoluteString == "https://test.example.com/api/v1/zip-lookup?zip=10012")
        #expect(captured.first?.httpMethod == "GET")
    }
}

private func makeStubbedSession() -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [StubURLProtocol.self]
    return URLSession(configuration: config)
}

private func response(for request: URLRequest, status: Int) -> HTTPURLResponse {
    HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: nil)!
}

/// Static-handler URLProtocol stub. The owning suite runs `.serialized`, so
/// only one test mutates the handler at a time.
final class StubURLProtocol: URLProtocol {
    private static let lock = NSLock()
    private static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?
    private static var requests: [URLRequest] = []

    static func setHandler(_ handler: @escaping (URLRequest) throws -> (HTTPURLResponse, Data)) {
        lock.lock()
        defer { lock.unlock() }
        Self.handler = handler
        Self.requests = []
    }

    static func reset() {
        lock.lock()
        defer { lock.unlock() }
        handler = nil
        requests = []
    }

    static var capturedRequests: [URLRequest] {
        lock.lock()
        defer { lock.unlock() }
        return requests
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.lock.lock()
        Self.requests.append(request)
        let handler = Self.handler
        Self.lock.unlock()

        guard let handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.unknown))
            return
        }

        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
