import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LibraryView: View {
    static let title = "Library"

    let apiClient: Client

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                LaughTrackHeroModule(
                    eyebrow: "Library",
                    title: Self.title,
                    subtitle: "Saved comedians, recent shows, and your tracked plans live here."
                )

                LaughTrackInlineStateCard(
                    tone: .empty,
                    title: "Library is filling in",
                    message: "Saved comedians arrive here next. For now, follow comics from anywhere in the app."
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.libraryTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle(Self.title)
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }
}
