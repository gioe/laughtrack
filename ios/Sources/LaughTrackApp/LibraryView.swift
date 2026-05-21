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
    let searchNavigationBridge: SearchNavigationBridge

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge
    ) {
        self.apiClient = apiClient
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
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
                        searchNavigationBridge: searchNavigationBridge,
                        cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
                        persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
                    )
                } else {
                    GuestFavoritesPreview()
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

            Text("Saved comedians, podcasts, and the shows and clubs connected to them.")
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
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
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
                FavoriteClubsSection(apiClient: apiClient)
            }

            if includes(.podcasts) {
                FavoritePodcastsSection(
                    apiClient: apiClient,
                    searchNavigationBridge: searchNavigationBridge
                )
            }
        }
        .task(id: requestKey) {
            await favoriteShowsModel.refresh(
                apiClient: apiClient,
                favoriteComedians: favoriteComedians,
                cache: cache,
                persistentCache: persistentCache
            )
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
        LibraryFavoritesPresentation.includes(primitive, selectedPrimitive: selectedPrimitive)
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
                FavoriteSearchableSection(
                    items: shows,
                    id: \.id,
                    searchPlaceholder: "Search favorite shows"
                ) { show, query in
                    LibraryFavoritesPresentation.matches(show: show, query: query)
                } row: { show in
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

private struct FavoriteClubsSection: View {
    let apiClient: Client

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    var body: some View {
        FavoriteSectionCard(
            identifier: LaughTrackViewTestID.favoritesClubsSection,
            eyebrow: "Clubs",
            title: "Saved clubs",
            subtitle: "Venues you've saved."
        ) {
            content
        }
    }

    @ViewBuilder
    private var content: some View {
        let laughTrack = theme.laughTrackTokens

        switch clubFavorites.savedFavoritesPhase {
        case .idle, .loading:
            LaughTrackStateView(
                tone: .loading,
                title: "Loading saved clubs",
                message: "LaughTrack is fetching your saved clubs from your account."
            )
        case .empty:
            LaughTrackStateView(
                tone: .empty,
                title: "No saved clubs yet",
                message: "Tap the heart on any club and it will appear here for this account."
            )
        case .failure(let failure):
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                LaughTrackStateView(
                    tone: .error,
                    title: "Couldn’t load saved clubs",
                    message: failure.message
                )
                LaughTrackButton(
                    "Retry clubs",
                    systemImage: "arrow.clockwise"
                ) {
                    Task {
                        await clubFavorites.loadSavedFavorites(
                            apiClient: apiClient,
                            authManager: authManager,
                            force: true
                        )
                    }
                }
            }
        case .loaded:
            FavoriteSearchableSection(
                items: clubFavorites.savedFavoriteClubs,
                id: \.id,
                searchPlaceholder: "Search saved clubs"
            ) { club, query in
                club.name.localizedCaseInsensitiveContains(query)
            } row: { club in
                Button {
                    coordinator.push(.clubDetail(club.id))
                } label: {
                    LaughTrackEntityRow(
                        title: club.name,
                        systemImage: "building.2",
                        imageURL: club.imageUrl,
                        showsDisclosureIndicator: true,
                        design: .savedEntity
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct FavoritePodcastsSection: View {
    let apiClient: Client
    let searchNavigationBridge: SearchNavigationBridge

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        FavoriteSectionCard(
            identifier: LaughTrackViewTestID.favoritesPodcastsSection,
            eyebrow: "Podcasts",
            title: "Saved podcasts",
            subtitle: "Comedy podcasts you've saved."
        ) {
            VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
                switch podcastFavorites.savedFavoritesPhase {
                case .idle, .loading:
                    LaughTrackStateView(
                        tone: .loading,
                        title: "Loading saved podcasts",
                        message: "LaughTrack is fetching your saved podcasts from your account."
                    )
                case .empty:
                    LaughTrackStateView(
                        tone: .empty,
                        title: "No saved podcasts yet",
                        message: "Tap the heart on any podcast and it will appear here for this account.",
                        actionTitle: "Browse podcasts",
                        action: {
                            searchNavigationBridge.openSearch(
                                .init(pivot: .podcasts, query: "", shortcut: nil)
                            )
                        }
                    )
                case .failure(let failure):
                    VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
                        LaughTrackStateView(
                            tone: .error,
                            title: "Couldn’t load saved podcasts",
                            message: failure.message
                        )
                        LaughTrackButton(
                            "Retry podcasts",
                            systemImage: "arrow.clockwise"
                        ) {
                            Task {
                                await podcastFavorites.loadSavedFavorites(
                                    apiClient: apiClient,
                                    authManager: authManager,
                                    force: true
                                )
                            }
                        }
                    }
                case .loaded:
                    FavoriteSearchableSection(
                        items: podcastFavorites.savedFavoritePodcasts,
                        id: \.id,
                        searchPlaceholder: "Search saved podcasts"
                    ) { podcast, query in
                        LibraryFavoritesPresentation.matches(podcast: podcast, query: query)
                    } row: { podcast in
                        Button {
                            coordinator.push(.podcastDetail(podcast.id))
                        } label: {
                            LaughTrackEntityRow(
                                title: podcast.title,
                                subtitle: rowSubtitle(for: podcast),
                                systemImage: "headphones",
                                imageURL: podcast.imageUrl,
                                showsDisclosureIndicator: true,
                                design: .savedEntity
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func rowSubtitle(for podcast: Components.Schemas.FavoritePodcastItem) -> String? {
        var parts: [String] = []
        if let author = podcast.authorName?.trimmingCharacters(in: .whitespacesAndNewlines), !author.isEmpty {
            parts.append(author)
        }
        if podcast.episodeCount > 0 {
            parts.append(podcast.episodeCount == 1 ? "1 episode" : "\(podcast.episodeCount) episodes")
        }
        return parts.isEmpty ? nil : parts.joined(separator: " • ")
    }
}

enum LibraryFavoritesPresentation {
    static func includes(
        _ primitive: SearchRootModel.Pivot,
        selectedPrimitive: SearchRootModel.Pivot?
    ) -> Bool {
        selectedPrimitive == nil || selectedPrimitive == primitive
    }

    static func matches(show: Components.Schemas.Show, query: String) -> Bool {
        if let name = show.name, name.localizedCaseInsensitiveContains(query) {
            return true
        }
        if let clubName = show.clubName, clubName.localizedCaseInsensitiveContains(query) {
            return true
        }
        if let lineup = show.lineup {
            for comedian in lineup {
                if comedian.name.localizedCaseInsensitiveContains(query) {
                    return true
                }
                if let parent = comedian.parentComedian,
                   parent.name.localizedCaseInsensitiveContains(query) {
                    return true
                }
            }
        }
        return false
    }

    static func matches(podcast: Components.Schemas.FavoritePodcastItem, query: String) -> Bool {
        if podcast.title.localizedCaseInsensitiveContains(query) {
            return true
        }
        if let author = podcast.authorName, author.localizedCaseInsensitiveContains(query) {
            return true
        }
        return false
    }
}

private struct GuestFavoritesPreview: View {
    @Environment(\.appTheme) private var theme

    private static let sampleShows = [
        ("Sample Club One", "Tonight · Headliner, opener"),
        ("Sample Club Two", "Tomorrow · Headliner"),
        ("Sample Club Three", "Saturday · Headliner"),
    ]
    private static let sampleComedians = [
        "Comedian One",
        "Comedian Two",
        "Comedian Three",
        "Comedian Four",
    ]
    private static let sampleClubs = [
        ("Sample Club One", "Headliners every weekend"),
        ("Sample Club Two", "Saved by you"),
        ("Sample Club Three", "Local favorite"),
    ]
    private static let samplePodcasts = [
        ("Sample Podcast One", "Sample Host · 120 episodes"),
        ("Sample Podcast Two", "Sample Host · 78 episodes"),
        ("Sample Podcast Three", "Sample Host · 42 episodes"),
    ]

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
            TeaserSection(
                eyebrow: "Shows",
                title: "Shows from favorites",
                subtitle: "Upcoming dates featuring comedians you've saved."
            ) {
                ForEach(Self.sampleShows, id: \.0) { name, detail in
                    TeaserRow(title: name, subtitle: detail)
                }
            }

            TeaserSection(
                eyebrow: "Comedians",
                title: "Saved comedians",
                subtitle: "Tap a comedian to follow their dates."
            ) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: theme.spacing.sm) {
                        ForEach(Self.sampleComedians, id: \.self) { name in
                            VStack(spacing: theme.spacing.xs) {
                                Circle()
                                    .fill(tokens.colors.textSecondary.opacity(0.15))
                                    .frame(width: 64, height: 64)
                                Text(name)
                                    .font(tokens.typography.metadata)
                                    .foregroundStyle(tokens.colors.textSecondary.opacity(0.55))
                                    .lineLimit(1)
                                    .redacted(reason: .placeholder)
                            }
                            .frame(width: 80)
                        }
                    }
                }
            }

            TeaserSection(
                eyebrow: "Clubs",
                title: "Saved clubs",
                subtitle: "Venues you've saved."
            ) {
                ForEach(Self.sampleClubs, id: \.0) { name, detail in
                    TeaserRow(title: name, subtitle: detail)
                }
            }

            TeaserSection(
                eyebrow: "Podcasts",
                title: "Saved podcasts",
                subtitle: "Comedy podcasts you've saved."
            ) {
                ForEach(Self.samplePodcasts, id: \.0) { name, detail in
                    TeaserRow(title: name, subtitle: detail)
                }
            }

            LaughTrackInlineStateCard(
                tone: .empty,
                title: LibraryView.signedOutPromptTitle,
                message: "Open Profile to sign in. Your saved comedians and the shows and clubs tied to them follow your account."
            )
        }
    }
}

private struct TeaserSection<Content: View>: View {
    let eyebrow: String
    let title: String
    let subtitle: String
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
            LaughTrackSectionHeader(eyebrow: eyebrow, title: title, subtitle: subtitle)
            LaughTrackCard {
                VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                    content
                }
            }
        }
    }
}

private struct TeaserRow: View {
    let title: String
    let subtitle: String

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        HStack(spacing: theme.spacing.sm) {
            RoundedRectangle(cornerRadius: 8)
                .fill(tokens.colors.textSecondary.opacity(0.15))
                .frame(width: 40, height: 40)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(tokens.typography.cardTitle)
                    .foregroundStyle(tokens.colors.textPrimary.opacity(0.6))
                    .redacted(reason: .placeholder)
                Text(subtitle)
                    .font(tokens.typography.metadata)
                    .foregroundStyle(tokens.colors.textSecondary.opacity(0.6))
                    .redacted(reason: .placeholder)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, theme.spacing.xs)
    }
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
