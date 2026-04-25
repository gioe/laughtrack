#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("Browse components")
@MainActor
struct LaughTrackBrowseComponentsTests {
    @Test("hero module uses compact browse copy hierarchy")
    func heroModuleUsesCompactHierarchy() async throws {
        let host = HostedView(
            LaughTrackHeroModule(
                eyebrow: "Nearby",
                title: "Tonight in San Francisco",
                subtitle: "Three strong options within 25 miles.",
                ctaTitle: "Open Search"
            )
            .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Tonight in San Francisco")
        try host.requireText("Three strong options within 25 miles.")
        try host.requireText("Open Search")
    }

    @Test("result row renders metadata in a dense browse row")
    func resultRowRendersMetadata() async throws {
        let host = HostedView(
            LaughTrackResultRow(
                title: "Comedy Cellar",
                subtitle: "New York, NY",
                metadata: ["14 shows", "Open tonight"],
                systemImage: "building.2"
            )
            .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Comedy Cellar")
        try host.requireText("New York, NY")
        try host.requireText("14 shows • Open tonight")
    }

    @Test("inline state card keeps retry affordance in compact chrome")
    func inlineStateCardRendersRetryAffordance() async throws {
        let host = HostedView(
            LaughTrackInlineStateCard(
                tone: .error,
                title: "Couldn't load this section",
                message: "Try refreshing this shelf.",
                actionTitle: "Try again",
                action: {}
            )
            .environment(\.appTheme, LaughTrackTheme())
        )

        try host.requireText("Couldn't load this section")
        try host.requireText("Try refreshing this shelf.")
        try host.requireText("Try again")
    }
}
#endif
