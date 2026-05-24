import Foundation

/// Test-only URLProtocol that serves deterministic responses for URLSession-driven tests.
final class StubURLProtocol: URLProtocol {
    typealias Handler = @Sendable (URLRequest) throws -> (HTTPURLResponse, Data)

    nonisolated(unsafe) static private(set) var lastRequest: URLRequest?

    private struct Stub {
        let handler: Handler
        let capturesLastRequest: Bool
    }

    private static let lock = NSLock()
    private static let stubIDHeader = "X-LaughTrack-Stub-URLProtocol-ID"
    nonisolated(unsafe) private static var stubs: [String: Stub] = [:]

    static func makeSession(
        handler: @escaping Handler,
        capturesLastRequest: Bool = false
    ) -> URLSession {
        let stubID = UUID().uuidString
        lock.withLock {
            stubs[stubID] = Stub(handler: handler, capturesLastRequest: capturesLastRequest)
            if capturesLastRequest {
                lastRequest = nil
            }
        }

        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        configuration.httpAdditionalHeaders = [stubIDHeader: stubID]
        return URLSession(configuration: configuration)
    }

    static func makeSession(json: String) -> URLSession {
        makeSession(handler: { request in
            let url = request.url ?? URL(string: "https://stub.invalid")!
            let response = HTTPURLResponse(
                url: url,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (response, Data(json.utf8))
        }, capturesLastRequest: true)
    }

    static func makeFailingSession(error: Error = URLError(.notConnectedToInternet)) -> URLSession {
        makeSession(handler: { _ in
            throw error
        }, capturesLastRequest: true)
    }

    override class func canInit(with request: URLRequest) -> Bool {
        request.value(forHTTPHeaderField: stubIDHeader) != nil
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard
            let stubID = request.value(forHTTPHeaderField: Self.stubIDHeader),
            let stub = Self.lock.withLock({ Self.stubs[stubID] })
        else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        if stub.capturesLastRequest {
            Self.lock.withLock {
                Self.lastRequest = request
            }
        }

        do {
            let (response, data) = try stub.handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
