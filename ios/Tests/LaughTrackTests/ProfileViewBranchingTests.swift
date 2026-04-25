import Testing
import LaughTrackCore
@testable import LaughTrackApp

@Suite("Profile view branching")
@MainActor
struct ProfileViewBranchingTests {
    @Test("signed-out hero title points users at sign-in")
    func signedOutHeroTitle() async throws {
        #expect(ProfileView.signedOutHeroTitle == "Sign in to LaughTrack")
    }

    @Test("signed-in hero title personalises with the auth provider name")
    func signedInHeroTitlePerProvider() async throws {
        #expect(ProfileView.heroTitle(for: .apple) == "Your Apple account")
        #expect(ProfileView.heroTitle(for: .google) == "Your Google account")
        #expect(ProfileView.heroTitle(for: nil) == "Your Saved session account")
    }
}
