import Combine
import CryptoKit
import Foundation
import LaughTrackBridge
import LaughTrackAPIClient
import OpenAPIURLSession
import Sentry
import FirebaseCore
import os

@MainActor
public struct AppBootstrap {
    public let container: ServiceContainer
    public let apiBaseURL: URL
    public let authManager: AuthManager
    public let apiClient: Client
    public let theme: LaughTrackTheme
    private let analyticsLifecycleCancellables: Set<AnyCancellable>
    private static let sentryTestCrashArgument = "SENTRY_TEST_CRASH"
    private static var sentryStarted = false
    private static var firebaseConfigured = false
    private static let analyticsLogger = Logger(subsystem: "com.laughtrack.analytics", category: "bootstrap")

    public init(
        container: ServiceContainer? = nil,
        oauthSessionRunner: any OAuthSessionRunning = SystemOAuthSessionRunner(),
        theme: LaughTrackTheme = LaughTrackTheme()
    ) {
        Self.configureSentryIfNeeded()
        Self.scheduleSentryTestCrashIfRequested()
        Self.configureFirebaseIfNeeded()

        let container = container ?? ServiceContainer()
        ServiceRegistration.configure(container)
        Self.configureAnalytics(container)
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
        authManager.pushTokenManager = container.resolveOptional((any PushDeviceTokenManaging).self)
        self.authManager = authManager

        self.analyticsLifecycleCancellables = Self.attachAnalyticsLifecycle(
            authManager: authManager,
            analytics: container.resolve(AnalyticsManagerProtocol.self)
        )

        let unauthorizedMiddleware = UnauthorizedResponseMiddleware {
            await authManager.handleUnauthorizedResponse()
        }

        // The refresh client must NOT include factory.authMiddleware. The /auth/refresh
        // contract carries the refresh token in the request body; signing the request
        // with the (likely expired) access token would create a circular dependency
        // between the very thing being refreshed and the request that refreshes it.
        let refreshClient = Client(
            serverURL: factory.serverURL,
            configuration: .laughTrack,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                XTimezoneHeaderNormalizationMiddleware(),
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
            configuration: .laughTrack,
            transport: URLSessionTransport(),
            middlewares: [
                APIVersionPathMiddleware(),
                XTimezoneHeaderNormalizationMiddleware(),
                unauthorizedMiddleware,
                tokenRefreshMiddleware,
                factory.authMiddleware,
                factory.retryMiddleware,
                factory.loggingMiddleware,
            ]
        )
        self.apiClient = apiClient

        authManager.signoutRequest = { [apiClient] in
            // Throw on any non-OK response so AuthManager.signOut()'s catch
            // block fires and signoutErrorObserver receives the error. The
            // OpenAPI spec has no 5xx branch for POST /auth/signout, so a 500
            // decodes as Output.undocumented and would otherwise return
            // silently — leaving the observer blind to server-side failures.
            let response = try await apiClient.signout()
            guard case .ok = response else {
                throw URLError(.badServerResponse)
            }
        }

        authManager.deleteAccountRequest = { [apiClient] in
            let response = try await apiClient.deleteMe()
            guard case .ok = response else {
                throw URLError(.badServerResponse)
            }
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
                userId: body.data.userId,
                displayName: body.data.displayName,
                email: body.data.email,
                avatarURL: avatarURL,
                emailShowNotifications: body.data.emailShowNotifications,
                pushShowNotifications: body.data.pushShowNotifications,
                comedianOnboardingCompleted: body.data.comedianOnboardingCompleted,
                zipCode: body.data.zipCode,
                nearbyDistanceMiles: body.data.nearbyDistanceMiles
            )
        }

        ServiceRegistration.configureZipLocationResolver(container, apiClient: apiClient)
        ServiceRegistration.configureOfflineQueue(container, apiClient: apiClient)
    }

    private static func configureSentryIfNeeded() {
        guard !sentryStarted, let dsn = AppConfiguration.sentryDSN else { return }
        sentryStarted = true

        SentrySDK.start { options in
            options.dsn = dsn
            options.environment = AppConfiguration.sentryEnvironment
            options.releaseName = AppConfiguration.sentryReleaseIdentifier
            options.dist = AppConfiguration.sentryBuildNumber
            options.tracesSampleRate = 0.1
        }
    }

    private static func scheduleSentryTestCrashIfRequested() {
        let processInfo = ProcessInfo.processInfo
        let shouldCrash = processInfo.arguments.contains(sentryTestCrashArgument)
            || processInfo.environment["LAUGHTRACK_SENTRY_TEST_CRASH"] == "1"
        guard shouldCrash else { return }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            fatalError("LaughTrack Sentry test crash")
        }
    }

    /// FirebaseApp.configure() hard-crashes when GoogleService-Info.plist is
    /// missing from the main bundle. The plist is operator-provisioned (Firebase
    /// console → iOS app → download), so guard the call until it's dropped into
    /// ios/Resources/. While dormant, only the DEBUG console sink emits events.
    private static func configureFirebaseIfNeeded() {
        guard !firebaseConfigured else { return }
        guard Bundle.main.url(forResource: "GoogleService-Info", withExtension: "plist") != nil else {
            analyticsLogger.notice("GoogleService-Info.plist not bundled — Firebase Analytics dormant; drop the plist into ios/Resources/ to activate.")
            return
        }
        FirebaseApp.configure()
        firebaseConfigured = true
    }

    /// Subscribes the analytics manager to AuthManager's user lifecycle. Returns
    /// the cancellable set so the caller can store it on a long-lived owner —
    /// dropping the set tears the subscription down.
    ///
    /// `currentUser` is the single source of truth for "is a user signed in":
    /// `state` cycles through `.restoring` → `.signingIn` → `.authenticated` /
    /// `.signedOut` on every auth event, but those transitions don't all map to
    /// a user identity change (e.g. token refresh keeps the same user). The
    /// scan-pairwise pattern fires `setUserID` plus the cohort-filter user
    /// properties (`comedian_onboarding_completed`, `has_zip`) exactly once per
    /// nil → non-nil edge and `reset` exactly once per non-nil → nil edge,
    /// ignoring the initial replay of the published value (nil at subscription
    /// time) and in-place user updates like `markComedianOnboardingCompleted`
    /// (the latter means a user who completes onboarding mid-session keeps the
    /// `false` property value until the next sign-in).
    static func attachAnalyticsLifecycle(
        authManager: AuthManager,
        analytics: AnalyticsManagerProtocol
    ) -> Set<AnyCancellable> {
        var cancellables: Set<AnyCancellable> = []
        authManager.$currentUser
            .scan((AuthenticatedUser?.none, AuthenticatedUser?.none)) { acc, next in
                (acc.1, next)
            }
            .sink { previous, current in
                switch (previous, current) {
                case (nil, let user?):
                    analytics.setUserID(Self.stableAnalyticsUserID(forEmail: user.email))
                    analytics.setUserProperty(
                        user.comedianOnboardingCompleted ? "true" : "false",
                        forName: "comedian_onboarding_completed"
                    )
                    analytics.setUserProperty(
                        user.zipCode != nil ? "true" : "false",
                        forName: "has_zip"
                    )
                case (_?, nil):
                    analytics.reset()
                default:
                    break
                }
            }
            .store(in: &cancellables)
        return cancellables
    }

    /// SHA-256 of the lowercased email, prefixed with the algorithm so the
    /// hashing scheme is self-describing in downstream sinks. Forwarding the
    /// raw email to Firebase Analytics would violate Google's documented
    /// policy against passing PII (names, email, phone numbers) as the GA4
    /// `user_id` (FirebaseAnalyticsProvider.setUserID forwards directly to
    /// `Analytics.setUserID`); lowercasing first keeps the identifier stable
    /// across any backend case-normalization step.
    static func stableAnalyticsUserID(forEmail email: String) -> String {
        let digest = SHA256.hash(data: Data(email.lowercased().utf8))
        let hex = digest.map { String(format: "%02x", $0) }.joined()
        return "sha256:\(hex)"
    }

    private static func configureAnalytics(_ container: ServiceContainer) {
        let manager = container.resolve(AnalyticsManagerProtocol.self)
        // Query Firebase directly rather than reading the local firebaseConfigured
        // static. The two helpers no longer have to be invoked in a fixed order:
        // a future bootstrap reordering or a second call site that forgets
        // configureFirebaseIfNeeded will not silently skip provider attachment.
        if FirebaseApp.app() != nil {
            manager.addProvider(FirebaseAnalyticsProvider())
        }
        #if DEBUG
        manager.addProvider(ConsoleAnalyticsProvider())
        #endif
    }
}
