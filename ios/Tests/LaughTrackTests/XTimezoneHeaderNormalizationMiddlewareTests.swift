import Testing
import Foundation
import HTTPTypes
import OpenAPIRuntime
import LaughTrackCore

@Suite("XTimezoneHeaderNormalizationMiddleware")
struct XTimezoneHeaderNormalizationMiddlewareTests {

    // The generator's setHeaderFieldAsURI emits this exact percent-encoded form
    // for `America/New_York` and is what TASK-1836 captured on the wire.
    @Test("decodes percent-encoded slash to plain IANA identifier")
    func decodesPercentEncodedSlash() async throws {
        try await assertNormalized(input: "America%2FNew_York", expected: "America/New_York")
    }

    @Test("leaves plain IANA identifier untouched")
    func leavesPlainIdentifierUntouched() async throws {
        try await assertNormalized(input: "America/New_York", expected: "America/New_York")
    }

    @Test("decodes UTC variant (no-op decode but path is exercised)")
    func leavesUtcUntouched() async throws {
        try await assertNormalized(input: "UTC", expected: "UTC")
    }

    @Test("does not add an X-Timezone header when none was set")
    func doesNotAddMissingHeader() async throws {
        let middleware = XTimezoneHeaderNormalizationMiddleware()
        let request = HTTPRequest(method: .get, scheme: nil, authority: nil, path: "/")
        _ = try await middleware.intercept(
            request,
            body: nil,
            baseURL: URL(string: "https://example.com")!,
            operationID: "test"
        ) { req, _, _ in
            let name = HTTPField.Name("X-Timezone")!
            #expect(req.headerFields[name] == nil)
            return (HTTPResponse(status: .ok), nil)
        }
    }

    private func assertNormalized(input: String, expected: String) async throws {
        let middleware = XTimezoneHeaderNormalizationMiddleware()
        let name = HTTPField.Name("X-Timezone")!
        var request = HTTPRequest(method: .get, scheme: nil, authority: nil, path: "/")
        request.headerFields[name] = input
        _ = try await middleware.intercept(
            request,
            body: nil,
            baseURL: URL(string: "https://example.com")!,
            operationID: "test"
        ) { req, _, _ in
            #expect(req.headerFields[name] == expected)
            return (HTTPResponse(status: .ok), nil)
        }
    }
}
