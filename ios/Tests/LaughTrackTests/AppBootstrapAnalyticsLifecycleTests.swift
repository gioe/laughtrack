import Combine
import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore
import LaughTrackAPIClient

@Suite("AppBootstrap analytics lifecycle wiring")
struct AppBootstrapAnalyticsLifecycleTests {

    @Test("sign-in with server-issued userId forwards it verbatim to analytics.setUserID")
    @MainActor
    func signInWithUserIdForwardsItVerbatim() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        let user = AuthenticatedUser(
            userId: "clx9q2tk30000abcdef123456",
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

        // Server-issued userId is preferred: setUserID must receive it verbatim,
        // NOT the SHA-256 email hash. Documents that the analytics user stream
        // is keyed on the opaque server identifier, so email changes never
        // restart it. reset() must NOT fire on a sign-in transition.
        #expect(env.analytics.setUserIDCalls == ["clx9q2tk30000abcdef123456"])
        #expect(env.analytics.resetCallCount == 0)
    }

    @Test("sign-in with no userId falls back to the SHA-256 email hash")
    @MainActor
    func signInWithoutUserIdFallsBackToEmailHash() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessToken = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshToken = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessToken)&refreshToken=\(refreshToken)"
        )!
        // Rollout-window fixture: /v1/me response predates TASK-2612 and omits
        // userId — AuthenticatedUser.userId is nil, the analytics sink must
        // fall back to the SHA-256 email hash so the user stream keeps flowing.
        let user = AuthenticatedUser(
            displayName: "Test User",
            email: "user@example.com",
            avatarURL: nil,
            comedianOnboardingCompleted: true,
            zipCode: "94110"
        )
        env.authManager.loadUserRequest = { user }

        let cancellables = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        defer { _ = cancellables }

        await env.authManager.signIn(with: .google)

        #expect(env.analytics.setUserIDCalls == [AppBootstrap.stableAnalyticsUserID(forEmail: "user@example.com")])
        #expect(env.analytics.resetCallCount == 0)

        // The same nil → user transition dispatches the cohort-filter user
        // properties. snake_case keys are pinned by the assertion strings —
        // a future rename would break this test and force re-review against
        // the convention in ios/CLAUDE.md (Analytics > Event-naming).
        #expect(env.analytics.userPropertyCalls.map(\.name) == [
            "comedian_onboarding_completed",
            "has_zip",
        ])
        #expect(env.analytics.userPropertyCalls.map(\.value) == ["true", "true"])
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

        #expect(env.analytics.setUserIDCalls == [AppBootstrap.stableAnalyticsUserID(forEmail: "user@example.com")])
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
        #expect(env.analytics.setUserIDCalls == [AppBootstrap.stableAnalyticsUserID(forEmail: "user@example.com")])
        #expect(env.analytics.resetCallCount == 0)

        // The user-property dispatch is also tied to the sign-in edge, NOT to
        // in-place currentUser updates. Two property calls (from sign-in) is
        // the contract: a third pair after markComedianOnboardingCompleted
        // would mean the live-update path opted in without a follow-up to
        // reconcile the duplicate-dispatch question.
        #expect(env.analytics.userPropertyCalls.count == 2)
        #expect(env.analytics.userPropertyCalls.map(\.name) == [
            "comedian_onboarding_completed",
            "has_zip",
        ])
        #expect(env.analytics.userPropertyCalls.map(\.value) == ["false", "false"])
    }

    @Test("user-switching within one session emits setUserID(A), reset(), setUserID(B) in order")
    @MainActor
    func userSwitchingEmitsExpectedOrderedCalls() async {
        let env = AnalyticsLifecycleEnv.make()

        let accessTokenA = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshTokenA = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessTokenA)&refreshToken=\(refreshTokenA)"
        )!
        // Anchor user-switching ordering on the post-rollout userId branch —
        // production sign-ins normally carry a server-issued userId, so the
        // ordered-emission regression guard should pin that path rather than
        // the rollout-window email-hash fallback.
        let userA = AuthenticatedUser(
            userId: "user-id-alice-clx9q2tk30000",
            displayName: nil,
            email: "alice@example.com",
            avatarURL: nil
        )
        env.authManager.loadUserRequest = { userA }

        let cancellables = AppBootstrap.attachAnalyticsLifecycle(
            authManager: env.authManager,
            analytics: env.analytics
        )
        defer { _ = cancellables }

        await env.authManager.signIn(with: .google)
        await env.authManager.signOut()

        // Swap the user payload and the OAuth callback to a second account,
        // then sign in again from the same in-process AuthManager. The
        // scan-pairwise emitter relies on AuthManager.signIn routing through
        // clearSession (currentUser -> nil) on its way out; a future change
        // that dedups on previous != current alone could silently regress
        // this — pin the ordered emission as the regression anchor.
        let accessTokenB = AnalyticsLifecycleEnv.jwt(expirationOffset: 3600)
        let refreshTokenB = "opaque-refresh-token-\(UUID().uuidString)"
        env.oauthRunner.callbackURL = URL(
            string: "laughtrack://auth/callback?provider=google&accessToken=\(accessTokenB)&refreshToken=\(refreshTokenB)"
        )!
        let userB = AuthenticatedUser(
            userId: "user-id-bob-clx9q2tk30001",
            displayName: nil,
            email: "bob@example.com",
            avatarURL: nil
        )
        env.authManager.loadUserRequest = { userB }

        await env.authManager.signIn(with: .google)

        #expect(env.analytics.setUserIDCalls == [
            "user-id-alice-clx9q2tk30000",
            "user-id-bob-clx9q2tk30001",
        ])
        #expect(env.analytics.resetCallCount == 1)

        // The cohort-filter user properties must re-fire on every sign-in
        // edge — once for userA, once for userB. A regression that gates the
        // property dispatch on a static "has run before" flag (firing only
        // on the first sign-in) would still pass the setUserIDCalls /
        // resetCallCount assertions above; this assertion is the explicit
        // anchor for the per-sign-in contract. Both fixture users use the
        // default AuthenticatedUser initializer, so comedianOnboardingCompleted
        // defaults to false and zipCode defaults to nil — all four values
        // are "false".
        #expect(env.analytics.userPropertyCalls.map(\.name) == [
            "comedian_onboarding_completed",
            "has_zip",
            "comedian_onboarding_completed",
            "has_zip",
        ])
        #expect(env.analytics.userPropertyCalls.map(\.value) == [
            "false", "false", "false", "false",
        ])
    }

    @Test("stableAnalyticsUserID hashes the lowercased email as sha256:<64 hex chars>")
    @MainActor
    func stableAnalyticsUserIDHashesLowercasedEmail() {
        let mixed = AppBootstrap.stableAnalyticsUserID(forEmail: "User@Example.COM")
        let lower = AppBootstrap.stableAnalyticsUserID(forEmail: "user@example.com")

        // Case-insensitive collapse: backend normalization that lowercases
        // emails must not invalidate the per-user analytics stream.
        #expect(mixed == lower)
        #expect(mixed.hasPrefix("sha256:"))
        #expect(mixed.dropFirst("sha256:".count).count == 64)
        // No raw PII leaks into the identifier.
        #expect(!mixed.contains("@"))
        #expect(!mixed.lowercased().contains("user"))
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
