import SwiftUI
import LaughTrackCore
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIURLSession

@main
struct LaughTrackApp: App {
    @StateObject private var coordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var authManager: AuthManager

    private let container: ServiceContainer
    private let apiClientFactory: APIClientFactory
    private let apiClient: Client

    init() {
        let container = ServiceContainer()
        ServiceRegistration.configure(container)
        self.container = container

        let secureStorage = container.resolveOptional(SecureStorageProtocol.self) ?? KeychainStorage()
        let appStateStorage = container.resolveOptional(AppStateStorageProtocol.self) ?? AppStateStorage()

        let factory = APIClientFactory(
            serverURL: AppConfiguration.apiBaseURL,
            secureStorage: secureStorage
        )
        self.apiClientFactory = factory

        let authManager = AuthManager(
            tokenManager: AuthTokenManager(secureStorage: secureStorage),
            authMiddleware: factory.authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: SystemOAuthSessionRunner()
        )
        _authManager = StateObject(wrappedValue: authManager)

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware {
            await authManager.handleUnauthorizedResponse()
        }

        // Plain client for token refresh (excludes TokenRefreshMiddleware to avoid loops)
        let refreshClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [factory.authMiddleware, factory.retryMiddleware, factory.loggingMiddleware]
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
            // LaughTrack issues a single JWT — use it as both access and refresh token
            return TokenRefreshMiddleware.Tokens(accessToken: token, refreshToken: token)
        }

        // Main client with full middleware chain including token refresh
        let apiClient = Client(
            serverURL: factory.serverURL,
            transport: URLSessionTransport(),
            middlewares: [tokenRefreshMiddleware, unauthorizedMiddleware, factory.authMiddleware, factory.retryMiddleware, factory.loggingMiddleware]
        )
        self.apiClient = apiClient

        ServiceRegistration.configureOfflineQueue(container, apiClient: apiClient)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        }
    }
}
