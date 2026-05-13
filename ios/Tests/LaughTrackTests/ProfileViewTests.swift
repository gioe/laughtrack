import Foundation
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

// TASK-2021: under iOS 26.1+ on iPhone 17, HostedView no longer wires the
// SwiftUI accessibility tree (see ios/CLAUDE.md "iOS 26 Accessibility-Tree
// Wiring Regression"), so the prior host.requireView / requireText /
// requireLabel assertions failed unconditionally. These tests now exercise
// AuthManager state and ProfileView's pure hero-text helpers directly, plus
// a deleteAccountRequest recorder for the dialog destructive-button path —
// none depend on the broken accessibility wiring.
@Suite("Profile view")
@MainActor
struct ProfileViewTests {
    @Test("profile settings and account copy seams stay stable")
    func profileCopySeamsStayStable() {
        #expect(ProfileView.profileSettingsTitle == "Profile settings")
        #expect(ProfileView.favoriteComedianAlertsTitle == "Favorite comedian alerts")
        #expect(ProfileView.signOutButtonTitle == "Sign out")
        #expect(ProfileView.deleteAccountButtonTitle == "Delete account")
    }

    @Test("signed-out auth state surfaces guest-mode hero text and gates settings off")
    func signedOutAuthStateProducesGuestHero() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "profile-signed-out")

        // ProfileView.body branches on these — both nil means the account card
        // and ProfileSettingsSection are not rendered, replacing the original
        // "settings panel hidden" assertions.
        #expect(authManager.currentSession == nil)
        #expect(authManager.currentUser == nil)

        #expect(ProfileView.makeHeroTitle(user: nil, session: nil) == "Guest mode")
        #expect(
            ProfileView.makeHeroSubtitle(user: nil, session: nil)
                == "Sign in to sync favorites and recover your account."
        )

        // Middle branch: session restored before loadUserRequest resolves
        // (or it returns nil). Locks in the "<provider> account" / "Favorites
        // sync through <provider> is on." path so a regression that swaps the
        // helpers' if-let order would not pass on the endpoint cases alone.
        let sessionWithoutUser = AuthSessionMetadata(
            provider: .apple,
            signedInAt: Date(),
            expiresAt: nil
        )
        #expect(
            ProfileView.makeHeroTitle(user: nil, session: sessionWithoutUser) == "Apple account"
        )
        #expect(
            ProfileView.makeHeroSubtitle(user: nil, session: sessionWithoutUser)
                == "Favorites sync through Apple is on."
        )
    }

    @Test("signed-in auth state surfaces display-name hero and unlocks settings panel")
    func signedInAuthStateProducesDisplayNameHero() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "profile-signed-in"
        )
        let user = AuthenticatedUser(
            displayName: "Ada Lovelace",
            email: "ada@example.com",
            avatarURL: nil,
            zipCode: "94108",
            nearbyDistanceMiles: 25
        )
        authManager.loadUserRequest = { user }
        await authManager.refreshCurrentUser()

        guard let session = authManager.currentSession else {
            Issue.record("Expected currentSession to be non-nil after authenticating")
            return
        }
        // currentUser != nil is the gate ProfileView.body uses to mount
        // ProfileSettingsSection (which carries the "Profile settings" /
        // "Favorite comedian alerts" copy the original assertions verified).
        #expect(authManager.currentUser == user)

        #expect(ProfileView.makeHeroTitle(user: user, session: session) == "Ada Lovelace")
        #expect(
            ProfileView.makeHeroSubtitle(user: user, session: session)
                == "Favorites sync is on for Ada Lovelace."
        )
    }

    @Test("authManager.deleteAccount() invokes deleteAccountRequest and drains the local session")
    func deleteAccountInvokesRequestAndDrainsSession() async throws {
        // The dialog's "Delete account permanently" destructive button is the
        // only call site for AuthManager.deleteAccount() in ProfileView; that
        // tap path requires accessibility wiring iOS 26.1 no longer provides.
        // This recorder verifies the back-half of the gating contract — that
        // when the destructive button DOES invoke deleteAccount, the request
        // closure fires once and the local session is drained.
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "profile-delete-confirm"
        )
        let user = AuthenticatedUser(
            displayName: "Ada Lovelace",
            email: "ada@example.com",
            avatarURL: nil
        )
        authManager.loadUserRequest = { user }
        await authManager.refreshCurrentUser()

        let recorder = DeleteAccountRecorder()
        authManager.deleteAccountRequest = { @Sendable in
            await recorder.record()
        }

        let initialCallCount = await recorder.callCount
        #expect(initialCallCount == 0)
        #expect(authManager.currentSession != nil)

        try await authManager.deleteAccount()

        let finalCallCount = await recorder.callCount
        #expect(finalCallCount == 1)
        #expect(authManager.currentSession == nil)
        #expect(authManager.currentUser == nil)
    }
}

private actor DeleteAccountRecorder {
    private(set) var callCount = 0

    func record() {
        callCount += 1
    }
}
