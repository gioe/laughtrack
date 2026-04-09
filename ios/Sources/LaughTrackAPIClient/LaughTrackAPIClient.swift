import APIClient

// MARK: - Re-exported API Types

/// Re-export APIClientFactory so the app target can initialize it.
public typealias APIClientFactory = APIClient.APIClientFactory
public typealias AuthenticationMiddleware = APIClient.AuthenticationMiddleware
public typealias LoggingMiddleware = APIClient.LoggingMiddleware
public typealias RetryMiddleware = APIClient.RetryMiddleware
public typealias TokenRefreshMiddleware = APIClient.TokenRefreshMiddleware

// Add product-specific extensions on generated types here.
// Example:
// extension Components.Schemas.User {
//     var displayName: String { "\(firstName) \(lastName)" }
// }
