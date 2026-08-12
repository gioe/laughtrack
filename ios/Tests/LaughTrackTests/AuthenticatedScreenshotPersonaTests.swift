import Testing
@testable import LaughTrackApp

@Suite("Authenticated screenshot persona")
struct AuthenticatedScreenshotPersonaTests {
    @Test("fixture is deterministic, useful, and contains no credentials")
    func deterministicCredentialsFreeFixture() {
        let first = AuthenticatedScreenshotPersona.shared
        let second = AuthenticatedScreenshotPersona.shared

        #expect(first == second)
        #expect(first.user.displayName == "Jordan Rivera")
        #expect(first.user.zipCode == "10012")
        #expect(first.favoriteComedians.count >= 2)
        #expect(first.upcomingSavedShows.map(\.title) == [
            "Atsuko Okatsuka: Full Grown Tour",
            "Josh Johnson and Friends",
        ])
        #expect(first.favoriteClubs == ["The Comedy Cellar"])
        #expect(first.favoritePodcasts == ["Good One: A Podcast About Jokes"])
        #expect(first.notifications.count == 2)
        #expect(first.notifications.filter(\.isUnread).count == 1)
        #expect(first.notifications.map(\.body) == [
            "The Comedy Cellar on Saturday at 8:00 PM",
            "The Comedy Cellar and The Bell House",
        ])
        #expect(first.notifications.allSatisfy { $0.sentAt != nil })
        #expect(first.user.avatarURL == nil)
        #expect(first.user.email.hasSuffix(".invalid"))
    }
}
