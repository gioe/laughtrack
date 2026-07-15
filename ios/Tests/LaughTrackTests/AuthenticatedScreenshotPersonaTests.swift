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
        #expect(first.notifications.count == 2)
        #expect(first.notifications.filter(\.isUnread).count == 1)
        #expect(first.user.email.hasSuffix(".invalid"))
    }
}
