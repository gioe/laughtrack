import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("Browse components")
struct LaughTrackBrowseComponentsTests {
    @Test("hero module uses compact browse copy hierarchy")
    func heroModuleUsesCompactHierarchy() {
        let module = LaughTrackHeroModule(
            eyebrow: "Nearby",
            title: "Tonight in San Francisco",
            subtitle: "Three strong options within 25 miles.",
            ctaTitle: "Open Search"
        )

        #expect(module.eyebrow == "Nearby")
        #expect(module.title == "Tonight in San Francisco")
        #expect(module.subtitle == "Three strong options within 25 miles.")
        #expect(module.ctaTitle == "Open Search")
    }

    @Test("result row renders metadata in a dense browse row")
    func resultRowRendersMetadata() {
        let row = LaughTrackResultRow(
            title: "Comedy Cellar",
            subtitle: "New York, NY",
            metadata: ["14 shows", "Open tonight"],
            systemImage: "building.2"
        )

        #expect(row.title == "Comedy Cellar")
        #expect(row.subtitle == "New York, NY")
        #expect(row.metadata.joined(separator: " • ") == "14 shows • Open tonight")
        #expect(row.systemImage == "building.2")
    }

    @Test("inline state card keeps retry affordance in compact chrome")
    func inlineStateCardRendersRetryAffordance() {
        let state = LaughTrackInlineStateCard(
            tone: .error,
            title: "Couldn't load this section",
            message: "Try refreshing this shelf.",
            actionTitle: "Try again",
            action: {}
        )

        #expect(state.title == "Couldn't load this section")
        #expect(state.message == "Try refreshing this shelf.")
        #expect(state.actionTitle == "Try again")
    }
}
