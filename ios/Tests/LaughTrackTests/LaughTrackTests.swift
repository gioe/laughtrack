import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("LaughTrack bootstrap")
struct LaughTrackTests {
    @Test("bootstrap composes the launch dependencies the app expects")
    @MainActor
    func bootstrapComposesLaunchDependencies() {
        let bootstrap = AppBootstrap(oauthSessionRunner: MockOAuthSessionRunner())

        #expect(bootstrap.apiBaseURL == AppConfiguration.apiBaseURL)
        #expect(bootstrap.authManager.state == AuthManager.State.restoring)
        #expect(bootstrap.container.resolveOptional(NetworkMonitorProtocol.self) != nil)
        #expect(bootstrap.container.resolveOptional(SecureStorageProtocol.self) != nil)
        #expect(bootstrap.container.resolveOptional(AppStateStorageProtocol.self) != nil)
        #expect(bootstrap.container.resolveOptional(DataCache<LaughTrackCacheKey>.self) != nil)
        #expect(bootstrap.container.resolveOptional(OfflineOperationQueue<LaughTrackOfflineOperation>.self) != nil)
    }

    @Test("app configuration startup invariants stay aligned with production URLs")
    func startupConfigurationMatchesProductionContracts() {
        #expect(AppConfiguration.apiBaseURL.scheme == "https")
        #expect(AppConfiguration.apiBaseURL.host == "laughtrack.app")
        #expect(AppConfiguration.apiBaseURL.path.isEmpty)
        #expect(AppConfiguration.bundleID == "com.laughtrack.laughtrack")
    }

    @Test("route definitions keep the launch-visible destinations stable")
    func routeDefinitionsRemainDistinct() {
        let googleSignInURL = AuthRouteConfiguration.signInURL(for: .google)
        let appleSignInURL = AuthRouteConfiguration.signInURL(for: .apple)
        let callbackURL = AuthRouteConfiguration.nativeCallbackURL(for: .google)

        #expect(AuthRouteConfiguration.callbackScheme == "laughtrack")
        #expect(googleSignInURL.host == "laughtrack.app")
        #expect(googleSignInURL.path == "/api/auth/signin/google")
        #expect(appleSignInURL.path == "/api/auth/signin/apple")
        #expect(callbackURL.path == "/api/v1/auth/native/callback")
        #expect(URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?.queryItems?.first?.value == "google")
    }

    @Test("bootstrap theme keeps bridge semantics available at launch")
    @MainActor
    func bootstrapThemeExposesExpectedBridgeContracts() {
        let bootstrap = AppBootstrap(oauthSessionRunner: MockOAuthSessionRunner())

        #expect(bootstrap.theme.spacing.section == bootstrap.theme.laughTrack.spacing.sectionGap)
        #expect(bootstrap.theme.cornerRadius.full == bootstrap.theme.laughTrack.radius.pill)
        #expect(bootstrap.theme.typography.button == bootstrap.theme.laughTrack.typography.action)
        #expect(bootstrap.theme.laughTrackTokens.colors.accent == bootstrap.theme.laughTrack.colors.accent)
    }
}

private final class MockOAuthSessionRunner: OAuthSessionRunning {
    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        URL(string: "\(callbackScheme)://auth/callback")!
    }
}
