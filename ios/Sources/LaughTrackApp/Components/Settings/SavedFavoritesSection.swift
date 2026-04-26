import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct SavedFavoritesSection: View {
    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Favorites",
                title: "Saved comedians",
                subtitle: "Comedians you've saved."
            )

            LaughTrackCard {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    switch favorites.savedFavoritesPhase {
                    case .idle, .loading:
                        LaughTrackStateView(
                            tone: .loading,
                            title: "Loading saved favorites",
                            message: "LaughTrack is fetching your saved comedians from your account."
                        )
                    case .empty:
                        LaughTrackStateView(
                            tone: .empty,
                            title: "No saved favorites yet",
                            message: "Favorite a comedian anywhere in LaughTrack and it will appear here for this account."
                        )
                    case .failure(let failure):
                        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                            LaughTrackStateView(
                                tone: .error,
                                title: "Couldn’t load saved favorites",
                                message: failure.message
                            )
                            LaughTrackButton(
                                "Retry favorites",
                                systemImage: "arrow.clockwise"
                            ) {
                                Task {
                                    await favorites.loadSavedFavorites(
                                        apiClient: apiClient,
                                        authManager: authManager,
                                        force: true
                                    )
                                }
                            }
                        }
                    case .loaded:
                        ForEach(favorites.savedFavoriteComedians, id: \.uuid) { comedian in
                            Button {
                                coordinator.push(.comedianDetail(comedian.id))
                            } label: {
                                HStack(spacing: laughTrack.spacing.itemGap) {
                                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                                        Text(comedian.name)
                                            .font(laughTrack.typography.cardTitle)
                                            .foregroundStyle(laughTrack.colors.textPrimary)
                                        Text(
                                            comedian.showCount == 1
                                                ? "1 tracked show appearance"
                                                : "\(comedian.showCount) tracked show appearances"
                                        )
                                        .font(laughTrack.typography.body)
                                        .foregroundStyle(laughTrack.colors.textSecondary)
                                    }

                                    Spacer()

                                    Image(systemName: "chevron.right")
                                        .foregroundStyle(laughTrack.colors.textSecondary)
                                }
                                .padding(.vertical, laughTrack.spacing.tight)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.libraryFavoritesSection)
    }
}
