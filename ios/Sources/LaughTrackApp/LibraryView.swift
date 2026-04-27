import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LibraryView: View {
    static let title = "Library"
    static let signedOutPromptTitle = "Sign in to see your saved comedians"

    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
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

                if authManager.currentSession != nil {
                    SavedFavoritesSection(apiClient: apiClient)
                } else {
                    LaughTrackInlineStateCard(
                        tone: .empty,
                        title: Self.signedOutPromptTitle,
                        message: "Open Profile to sign in. Your saved comedians follow your account, not the device."
                    )
                }
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
