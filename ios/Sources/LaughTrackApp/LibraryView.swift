import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LibraryView: View {
    static let title = "Favorites"
    static let signedOutPromptTitle = "Sign in to see your favorites"

    let apiClient: Client
    let selectedPrimitive: SearchRootModel.Pivot?

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(apiClient: Client, selectedPrimitive: SearchRootModel.Pivot? = nil) {
        self.apiClient = apiClient
        self.selectedPrimitive = selectedPrimitive
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                FavoritesHeader()

                if authManager.currentSession != nil {
                    FavoritePrimitiveSections(
                        apiClient: apiClient,
                        selectedPrimitive: selectedPrimitive,
                        cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
                    )
                } else {
                    LaughTrackInlineStateCard(
                        tone: .empty,
                        title: Self.signedOutPromptTitle,
                        message: "Open Profile to sign in. Your saved comedians and the shows and clubs tied to them follow your account."
                    )
                }
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, -4)
            .padding(.bottom, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.favoritesTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle(Self.title)
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }
}

private struct FavoritesHeader: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text("Favorites")
                .font(tokens.typography.sectionTitle)
                .foregroundStyle(tokens.colors.textPrimary)
                .lineLimit(1)
                .minimumScaleFactor(0.85)

            Text("Saved comedians and the shows and clubs connected to them.")
                .font(tokens.typography.body)
                .foregroundStyle(tokens.colors.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(LaughTrackViewTestID.favoritesHeader)
    }
}

private struct FavoritePrimitiveSections: View {
    let apiClient: Client
    let selectedPrimitive: SearchRootModel.Pivot?
    let cache: DataCache<LaughTrackCacheKey>

    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @StateObject private var favoriteShowsModel = HomeFavoriteShowsModel()

    private var favoriteComedians: [Components.Schemas.ComedianSearchItem] {
        guard favorites.savedFavoritesPhase == .loaded else { return [] }

        return favorites.savedFavoriteComedians
    }

    private var requestKey: String {
        HomeFavoriteShowsModel.requestKey(for: favoriteComedians)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: themeSpacing) {
            if includes(.shows) {
                FavoriteShowsSection(
                    phase: favoriteShowsModel.phase,
                    favoriteListIsEmpty: favoriteListIsEmpty
                )
            }

            if includes(.comedians) {
                SavedFavoritesSection(apiClient: apiClient)
            }

            if includes(.clubs) {
                FavoriteClubsSection(
                    phase: favoriteShowsModel.phase,
                    favoriteListIsEmpty: favoriteListIsEmpty
                )
            }
        }
        .task(id: requestKey) {
            await favoriteShowsModel.refresh(apiClient: apiClient, favoriteComedians: favoriteComedians, cache: cache)
        }
    }

    @Environment(\.appTheme) private var theme

    private var themeSpacing: CGFloat {
        theme.laughTrackTokens.browseDensity.shelfGap
    }

    private var favoriteListIsEmpty: Bool {
        if case .empty = favorites.savedFavoritesPhase {
            return true
        }
        return false
    }

    private func includes(_ primitive: SearchRootModel.Pivot) -> Bool {
        selectedPrimitive == nil || selectedPrimitive == primitive
    }
}

private struct FavoriteShowsSection: View {
    let phase: LoadPhase<[Components.Schemas.Show]>
    let favoriteListIsEmpty: Bool

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    var body: some View {
        FavoriteSectionCard(
            identifier: LaughTrackViewTestID.favoritesShowsSection,
            eyebrow: "Shows",
            title: "Shows from favorites",
            subtitle: "Upcoming dates featuring comedians you've saved."
        ) {
            content
        }
    }

    @ViewBuilder
    private var content: some View {
        let tokens = theme.laughTrackTokens

        if favoriteListIsEmpty {
            LaughTrackStateView(
                tone: .empty,
                title: "No favorite shows yet",
                message: "Save comedians with upcoming dates and their shows will appear here."
            )
        } else {
            switch phase {
        case .idle, .loading:
            LaughTrackStateView(
                tone: .loading,
                title: "Loading favorite shows",
                message: "LaughTrack is checking upcoming dates for your saved comedians."
            )
        case .failure(let failure):
            LaughTrackStateView(
                tone: .error,
                title: "Couldn’t load favorite shows",
                message: failure.message
            )
        case .success(let shows) where shows.isEmpty:
            LaughTrackStateView(
                tone: .empty,
                title: "No favorite shows yet",
                message: "Save comedians with upcoming dates and their shows will appear here."
            )
        case .success(let shows):
            VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
                ForEach(shows.prefix(8), id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        }
    }
}

private struct FavoriteClubsSection: View {
    let phase: LoadPhase<[Components.Schemas.Show]>
    let favoriteListIsEmpty: Bool

    @Environment(\.appTheme) private var theme

    var body: some View {
        FavoriteSectionCard(
            identifier: LaughTrackViewTestID.favoritesClubsSection,
            eyebrow: "Clubs",
            title: "Clubs from favorites",
            subtitle: "Venues where your saved comedians have upcoming shows."
        ) {
            content
        }
    }

    @ViewBuilder
    private var content: some View {
        let tokens = theme.laughTrackTokens

        if favoriteListIsEmpty {
            LaughTrackStateView(
                tone: .empty,
                title: "No favorite clubs yet",
                message: "When saved comedians announce upcoming shows, their venues will appear here."
            )
        } else {
            switch phase {
        case .idle, .loading:
            LaughTrackStateView(
                tone: .loading,
                title: "Loading favorite clubs",
                message: "LaughTrack is deriving venues from your saved comedians' upcoming shows."
            )
        case .failure(let failure):
            LaughTrackStateView(
                tone: .error,
                title: "Couldn’t load favorite clubs",
                message: failure.message
            )
        case .success(let shows):
            let clubs = derivedClubs(from: shows)
            if clubs.isEmpty {
                LaughTrackStateView(
                    tone: .empty,
                    title: "No favorite clubs yet",
                    message: "When saved comedians announce upcoming shows, their venues will appear here."
                )
            } else {
                VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
                    ForEach(clubs, id: \.name) { club in
                        VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                            Text(club.name)
                                .font(tokens.typography.cardTitle)
                                .foregroundStyle(tokens.colors.textPrimary)
                            Text(club.showCount == 1 ? "1 favorite-comedian show" : "\(club.showCount) favorite-comedian shows")
                                .font(tokens.typography.body)
                                .foregroundStyle(tokens.colors.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, tokens.spacing.tight)
                    }
                }
            }
        }
        }
    }

    private func derivedClubs(from shows: [Components.Schemas.Show]) -> [FavoriteClubSummary] {
        let counts = shows.reduce(into: [String: Int]()) { result, show in
            guard let clubName = show.clubName?.trimmingCharacters(in: .whitespacesAndNewlines), !clubName.isEmpty else {
                return
            }
            result[clubName, default: 0] += 1
        }

        return counts
            .map { FavoriteClubSummary(name: $0.key, showCount: $0.value) }
            .sorted { lhs, rhs in
                if lhs.showCount != rhs.showCount {
                    return lhs.showCount > rhs.showCount
                }
                return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
            }
    }
}

private struct FavoriteClubSummary: Hashable {
    let name: String
    let showCount: Int
}

private struct FavoriteSectionCard<Content: View>: View {
    let identifier: String
    let eyebrow: String
    let title: String
    let subtitle: String
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: eyebrow,
                title: title,
                subtitle: subtitle
            )

            LaughTrackCard {
                content
            }
        }
        .accessibilityIdentifier(identifier)
    }
}
