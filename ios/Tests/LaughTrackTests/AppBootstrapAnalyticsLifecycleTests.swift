import Combine
import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore
import LaughTrackAPIClient

@Suite("AppBootstrap analytics lifecycle wiring")
struct AppBootstrapAnalyticsLifecycleTests {

    @Test("sign-in transition forwards the user's stable identifier to analytics.setUserID")
    @MainActor
    func signInForwardsUserIDToAnalytics() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        let user = AuthenticatedUser(
            displayName: "Test User",
            email: "user@example.com",
            avatarURL: nil
        )
        env.authManager.loadUserRequest = { user }

        let cancellables = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        defer { _ = cancellables }

        await env.authManager.signIn(with: .google)

        // setUserID must be called exactly once with the user's stable identifier
        // (currently `email` — the only stable per-account field on
        // AuthenticatedUser). reset() must NOT fire on a sign-in transition.
        #expect(env.analytics.setUserIDCalls == ["user@example.com"])
        #expect(env.analytics.resetCallCount == 0)
    }

    @Test("sign-out transition calls analytics.reset() after a prior sign-in")
    @MainActor
    func signOutCallsResetAfterPriorSignIn() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        let user = AuthenticatedUser(
            displayName: "Test User",
            email: "user@example.com",
            avatarURL: nil
        )
        env.authManager.loadUserRequest = { user }

        let cancellables = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        defer { _ = cancellables }

        await env.authManager.signIn(with: .google)
        await env.authManager.signOut()

        #expect(env.analytics.setUserIDCalls == ["user@example.com"])
        #expect(env.analytics.resetCallCount == 1)
    }

    @Test("subscription is no-op for the initial nil emission and same-user updates")
    @MainActor
    func initialNilAndSameUserUpdatesDoNotEmit() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        let user = AuthenticatedUser(
            displayName: "Test User",
            email: "user@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: false
        )
        env.authManager.loadUserRequest = { user }

        let cancellables = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        defer { _ = cancellables }

        // Initial subscription replays nil to the scan accumulator — no
        // setUserID and no reset should fire before any auth transition.
        #expect(env.analytics.setUserIDCalls.isEmpty)
        #expect(env.analytics.resetCallCount == 0)

        await env.authManager.signIn(with: .google)
        env.authManager.markComedianOnboardingCompleted()

        // markComedianOnboardingCompleted mutates currentUser in place. The
        // sign-in setUserID call is the only one; the in-place update must
        // not re-fire it, and reset() must stay at 0.
        #expect(env.analytics.setUserIDCalls == ["user@example.com"])
        #expect(env.analytics.resetCallCount == 0)
    }

    @Test("dropping the cancellable set tears down the subscription")
    @MainActor
    func droppingCancellablesTearsDownSubscription() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        env.authManager.loadUserRequest = {
            AuthenticatedUser(displayName: nil, email: "user@example.com", avatarURL: nil)
        }

        var cancellables: Set<AnyCancellable>? = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        _ = cancellables

        cancellables = nil

        await env.authManager.signIn(with: .google)

        // With the cancellable set dropped, the sink should no longer fire on
        // subsequent auth-state changes. Documents the "subscription lifetime
        // matches the cancellable set's lifetime" contract.
        #expect(env.analytics.setUserIDCalls.isEmpty)
        #expect(env.analytics.resetCallCount == 0)
    }
}

@MainActor
private struct AnalyticsLifecycleEnv {
    let authManager: AuthManager
    let analytics: RecordingAnalyticsManager
    let oauthRunner: AnalyticsLifecycleOAuthRunner

    static func make() -> AnalyticsLifecycleEnv {
        let secureStorage = InMemorySecureStorage()
        let appStateStorage = AppStateStorage(
            userDefaults: UserDefaults(
                suiteName: "AppBootstrapAnalyticsLifecycleTests.\(UUID().uuidString)"
            )!
        )
        let authMiddleware = AuthenticationMiddleware(secureStorage: secureStorage)
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        let runner = AnalyticsLifecycleOAuthRunner()
        let manager = AuthManager(
            tokenManager: tokenManager,
            authMiddleware: authMiddleware,
            appStateStorage: appStateStorage,
            oauthSessionRunner: runner
        )
        return AnalyticsLifecycleEnv(
            authManager: manager,
            analytics: RecordingAnalyticsManager(),
            oauthRunner: runner
        )
    }

    static func jwt(expirationOffset: TimeInterval) -> String {
        let header = #"{"alg":"HS256","typ":"JWT"}"#
        let payload = #"{"exp":\#(Int(Date().addingTimeInterval(expirationOffset).timeIntervalSince1970))}"#
        return "\(base64URL(header)).\(base64URL(payload)).signature"
    }

    private static func base64URL(_ string: String) -> String {
        Data(string.utf8)
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

private final class AnalyticsLifecycleOAuthRunner: OAuthSessionRunning, @unchecked Sendable {
    var callbackURL = URL(string: "laughtrack://auth/callback")!

    func authenticate(startURL: URL, callbackScheme: String) async throws -> URL {
        callbackURL
    }
}

@MainActor
private final class RecordingAnalyticsManager: AnalyticsManagerProtocol {
    private(set) var setUserIDCalls: [String?] = []
    private(set) var resetCallCount = 0
    private(set) var userPropertyCalls: [(name: String, value: String?)] = []

    nonisolated func addProvider(_ provider: AnalyticsProvider) {}

    nonisolated func track(_ event: AnalyticsEvent) {}

    nonisolated func track(_ name: String, parameters: [String: Any]?) {}

    nonisolated func trackScreen(_ name: String, parameters: [String: Any]?) {}

    nonisolated func setUserProperty(_ value: String?, forName name: String) {
        MainActor.assumeIsolated {
            userPropertyCalls.append((name: name, value: value))
        }
    }

    nonisolated func setUserID(_ userID: String?) {
        MainActor.assumeIsolated {
            setUserIDCalls.append(userID)
        }
    }

    nonisolated func reset() {
        MainActor.assumeIsolated {
            resetCallCount += 1
        }
    }
}
