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

        let authManager = AuthManager(
            tokenManager: AuthTokenManager(secureStorage: secureStorage),
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: oauthSessionRunner
        )
        self.authManager = authManager

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware {
            await authManager.handleUnauthorizedResponse()
        }

        let refreshClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )

        let tokenRefreshMiddleware = TokenRefreshMiddleware(
            authMiddleware: factory.authMiddleware,
            refreshEndpointOperationID: "exchangeToken"
        ) { _ in
            let response = try await refreshClient.exchangeToken()
            guard case .ok(let ok) = response else {
                await authManager.handleUnauthorizedResponse()
                throw URLError(.userAuthenticationRequired)
            }
            let token = try ok.body.json.token
            return TokenRefreshMiddleware.Tokens(accessToken: token, refreshToken: token)
        }

        let apiClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                tokenRefreshMiddleware,
                unauthorizedMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )
        self.apiClient = apiClient

        ServiceRegistration.configureOfflineQueue(container, apiClient: apiClient)
    }
}
