import SwiftUI
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

    @Test("chip picker maps the selected option to accent tone and updates through the binding")
    func chipPickerMapsSelectionToAccentTone() {
        var selection = 25
        let picker = LaughTrackChipPicker(
            options: [10, 25, 50],
            selection: Binding(get: { selection }, set: { selection = $0 }),
            accessibilityLabel: "Distance",
            accessibilityIdentifier: "test.distance-picker"
        ) { "\($0) mi" }

        #expect(picker.tone(for: 25) == .accent)
        #expect(picker.tone(for: 10) == .neutral)
        #expect(picker.title(50) == "50 mi")

        picker.selection = 50
        #expect(selection == 50)
        #expect(picker.tone(for: 50) == .accent)
        #expect(picker.tone(for: 25) == .neutral)
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
