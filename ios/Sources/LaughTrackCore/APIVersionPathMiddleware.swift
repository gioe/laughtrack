import Foundation
import HTTPTypes
import OpenAPIRuntime

/// Prefixes generated OpenAPI paths with the backend API mount point.
///
/// The generated client emits absolute paths like `/shows/search`, which causes
/// Foundation URL resolution to drop the `/api/v1` portion of the configured
/// server URL. Keeping the prefix in middleware lets the app target preserve the
/// checked-in OpenAPI spec while still reaching the mounted API routes.
public struct APIVersionPathMiddleware: ClientMiddleware {
    private let prefix: String

    public init(prefix: String = "/api/v1") {
        self.prefix = prefix.hasPrefix("/") ? prefix : "/\(prefix)"
    }

    public func intercept(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        var request = request

        if let path = request.path, !path.hasPrefix(prefix), !path.hasPrefix("http://"), !path.hasPrefix("https://") {
            if path.hasPrefix("/") {
                request.path = prefix + path
            } else {
                request.path = prefix + "/" + path
            }
        }

        return try await next(request, body, baseURL)
    }
}
