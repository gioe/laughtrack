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
                        FavoriteSearchableSection(
                            items: favorites.savedFavoriteComedians,
                            id: \.uuid,
                            searchPlaceholder: "Search saved comedians"
                        ) { comedian, query in
                            comedian.name.localizedCaseInsensitiveContains(query)
                        } row: { comedian in
                            Button {
                                coordinator.push(.comedianDetail(comedian.id))
                            } label: {
                                LaughTrackEntityRow(
                                    title: comedian.name,
                                    subtitle: Self.subtitle(for: comedian),
                                    systemImage: "person.fill",
                                    imageURL: comedian.imageUrl,
                                    showsDisclosureIndicator: true
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.favoritesComediansSection)
    }

    private static func subtitle(for comedian: Components.Schemas.ComedianSearchItem) -> String? {
        comedian.showCount == 1
            ? "1 tracked show appearance"
            : "\(comedian.showCount) tracked show appearances"
    }
}
