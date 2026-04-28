import Foundation
import HTTPTypes
import OpenAPIRuntime

/// Removes percent-encoding from the `X-Timezone` request header.
///
/// `swift-openapi-generator` emits `setHeaderFieldAsURI` for header parameters
/// when the OpenAPI spec declares no explicit `style`, which applies RFC 6570
/// URI Template encoding to the value. For an IANA identifier like
/// `America/New_York` that turns the `/` into `%2F` before the request leaves
/// the device. The LaughTrack server validates `X-Timezone` with
/// `Intl.DateTimeFormat` (TASK-1829), which rejects `America%2FNew_York` as a
/// non-IANA value with HTTP 400, breaking shows search, home feed, and
/// upcoming-shows rails on iOS. Per RFC 7230 `/` is allowed unencoded in HTTP
/// header values, so decoding the value here is contract-safe.
///
/// The middleware fixes the wire shape without regenerating the OpenAPI client
/// (the alternative would require a spec edit declaring `style`/`explode` on
/// each `X-Timezone` parameter and a lockstep Client.swift + Types.swift
/// regeneration per ios/CLAUDE.md). Runs uniformly across every route that
/// sends `X-Timezone`, so any future timezone-aware endpoint inherits the fix.
public struct XTimezoneHeaderNormalizationMiddleware: ClientMiddleware {
    public init() {}

    public func intercept(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        var request = request
        if let name = HTTPField.Name("X-Timezone"),
           let encoded = request.headerFields[name],
           let decoded = encoded.removingPercentEncoding,
           decoded != encoded {
            request.headerFields[name] = decoded
        }
        return try await next(request, body, baseURL)
    }
}
