import SwiftUI

struct ActivityView: View {
    static let title = "Activity"
    static let emptyStateMessage = "Followed comics, saved reminders, and venue alerts will show up here."

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                LaughTrackHeroModule(
                    eyebrow: "Activity",
                    title: Self.title,
                    subtitle: Self.emptyStateMessage
                )

                LaughTrackInlineStateCard(
                    tone: .empty,
                    title: "Nothing queued yet",
                    message: "As you follow comics and save plans, this tab will turn into your running feed."
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.activityTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle(Self.title)
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }
}
