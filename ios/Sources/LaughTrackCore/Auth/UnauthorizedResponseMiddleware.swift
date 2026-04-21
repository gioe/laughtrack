import Foundation
import HTTPTypes
import OpenAPIRuntime

public actor UnauthorizedResponseMiddleware: ClientMiddleware {
    private let onUnauthorized: @Sendable () async -> Void

    public init(onUnauthorized: @escaping @Sendable () async -> Void) {
        self.onUnauthorized = onUnauthorized
    }

    public func intercept(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String,
        next: @Sendable (HTTPRequest, HTTPBody?, URL) async throws -> (HTTPResponse, HTTPBody?)
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let result = try await next(request, body, baseURL)

        if result.0.status.code == 401 && operationID != "exchangeToken" {
            await onUnauthorized()
        }

        return result
    }
}
