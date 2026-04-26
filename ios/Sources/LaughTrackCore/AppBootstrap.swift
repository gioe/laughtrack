import Foundation
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIURLSession

@MainActor
public struct AppBootstrap {
    public let container: ServiceContainer
    public let apiBaseURL: URL
    public let authManager: AuthManager
    public let apiClient: Client
    public let theme: LaughTrackTheme

    public init(
        container: ServiceContainer? = nil,
        oauthSessionRunner: any OAuthSessionRunning = SystemOAuthSessionRunner(),
        theme: LaughTrackTheme = LaughTrackTheme()
    ) {
        let container = container ?? ServiceContainer()
        ServiceRegistration.configure(container)
        self.container = container
        self.apiBaseURL = AppConfiguration.apiBaseURL
        self.theme = theme

        let secureStorage = container.resolveOptional(SecureStorageProtocol.self) ?? KeychainStorage()
        let appStateStorage = container.resolveOptional(AppStateStorageProtocol.self) ?? AppStateStorage()

        let factory = APIClientFactory(
            serverURL: apiBaseURL,
            secureStorage: secureStorage
        )

        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let authManager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: oauthSessionRunner
        )
        self.authManager = authManager

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware {
            await authManager.handleUnauthorizedResponse()
        }

        // The refresh client must NOT include factory.authMiddleware. The /auth/refresh
        // contract carries the refresh token in the request body; signing the request
        // with the (likely expired) access token would create a circular dependency
        // between the very thing being refreshed and the request that refreshes it.
        let refreshClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: Operations.RefreshToken.id
        ) { _ in
            let refreshToken = await MainActor.run { tokenManager.retrieveRefreshToken() }
            guard let refreshToken else {
                await authManager.handleUnauthorizedResponse()
                throw URLError(.userAuthenticationRequired)
            }

            let response = try await refreshClient.refreshToken(
                body: .json(.init(refreshToken: refreshToken))
            )
            guard case .ok(let ok) = response, case .json(let body) = ok.body else {
                await authManager.handleUnauthorizedResponse()
                throw URLError(.userAuthenticationRequired)
            }

            // Persist the rotated pair to the keychain via AuthTokenManager so a cold
            // restart sees the new tokens. AuthenticationMiddleware also persists via
            // its own SecureStorage handle, but it bypasses AuthTokenManager's
            // @Published isAuthenticated state — keep both in sync.
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

        // OpenAPIRuntime wraps middlewares with `middlewares.reversed()`, so the first
        // array element is outermost on the response path. Unauthorized must sit outside
        // TokenRefresh so a successful 401 -> refresh -> retry cycle is invisible to it —
        // otherwise it would clear the session before TokenRefresh had a chance to rescue
        // the request.
        let apiClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )
        self.apiClient = apiClient

        authManager.signoutRequest = { [apiClient] in
            _ = try await apiClient.signout()
        }

        authManager.loadUserRequest = { [apiClient] in
            let response = try await apiClient.getMe()
            // Throw on non-200 so AuthManager.refreshCurrentUser keeps the
            // previously-loaded user instead of clobbering it on a transient
            // 401/422/429 (e.g. on a refetch after sign-in).
            guard case .ok(let ok) = response, case .json(let body) = ok.body else {
                throw URLError(.badServerResponse)
            }
            let avatarURL = body.data.avatarUrl.flatMap { URL(string: $0) }
            return AuthenticatedUser(
                displayName: body.data.displayName,
                email: body.data.email,
                avatarURL: avatarURL
            )
        }

        ServiceRegistration.configureZipLocationResolver(container, apiClient: apiClient)
        ServiceRegistration.configureOfflineQueue(container, apiClient: apiClient)
    }
}
