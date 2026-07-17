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
    /// Show ids from a notification tap; scopes the touring section (empty = all).
    let scopedShowIDs: [Int]
    let searchNavigationBridge: SearchNavigationBridge
    let screenshotPersona: AuthenticatedScreenshotPersona?

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        scopedShowIDs: [Int] = [],
        searchNavigationBridge: SearchNavigationBridge,
        screenshotPersona: AuthenticatedScreenshotPersona? = nil
    ) {
        self.apiClient = apiClient
        self.selectedPrimitive = selectedPrimitive
        self.scopedShowIDs = scopedShowIDs
        self.searchNavigationBridge = searchNavigationBridge
        self.screenshotPersona = screenshotPersona
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                if let screenshotPersona {
                    AuthenticatedFavoritesSnapshot(persona: screenshotPersona)
                } else if authManager.currentSession != nil {
                    FavoritePrimitiveSections(
                        apiClient: apiClient,
                        selectedPrimitive: selectedPrimitive,
                        scopedShowIDs: scopedShowIDs,
                        searchNavigationBridge: searchNavigationBridge,
                        cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
                        persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
                    )
                } else {
                    GuestFavoritesPreview()
                }
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, tokens.browseDensity.heroPadding)
        }
        .rootScrollBottomClearance(
            theme: theme,
            isPodcastMiniPlayerVisible: podcastPlayer.currentItem != nil
        )
        .accessibilityIdentifier(LaughTrackViewTestID.favoritesTabScreen)
        .background(LaughTrackAtmosphereBackground().ignoresSafeArea())
        .navigationTitle(Self.title)
        .modifier(LaughTrackNavigationChrome(background: .clear))
    }
}

private struct AuthenticatedFavoritesSnapshot: View {
    let persona: AuthenticatedScreenshotPersona

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens
        VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
            TeaserSection(
                eyebrow: "Favorites",
                title: "Your favorites are touring",
                subtitle: "Upcoming shows from comedians you follow."
            ) {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                        ForEach(persona.favoriteShows, id: \.title) { show in
                            TeaserRow(
                                title: show.title,
                                subtitle: show.detail,
                                systemImage: "calendar",
                                isPlaceholder: false
                            )
                        }
                    }
                }
            }

            TeaserSection(
                eyebrow: "Comedians",
                title: "Saved comedians",
                subtitle: "We'll keep their nearby dates in one place."
            ) {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                        ForEach(persona.favoriteComedians, id: \.self) { name in
                            TeaserRow(
                                title: name,
                                subtitle: "Following · notifications on",
                                systemImage: "person.fill",
                                isPlaceholder: false
                            )
                        }
                    }
                }
            }

            TeaserSection(
                eyebrow: "Clubs",
                title: "Saved clubs",
                subtitle: "Keep favorite venue calendars close."
            ) {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                        ForEach(persona.favoriteClubs, id: \.self) { name in
                            TeaserRow(
                                title: name,
                                subtitle: "Saved venue",
                                systemImage: "building.2.fill",
                                isPlaceholder: false
                            )
                        }
                    }
                }
            }

            TeaserSection(
                eyebrow: "Podcasts",
                title: "Saved podcasts",
                subtitle: "Find new episodes faster."
            ) {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                        ForEach(persona.favoritePodcasts, id: \.self) { title in
                            TeaserRow(
                                title: title,
                                subtitle: "Vulture · 248 episodes",
                                systemImage: "mic.fill",
                                isPlaceholder: false
                            )
                        }
                    }
                }
            }
        }
    }
}

private struct FavoritePrimitiveSections: View {
    let apiClient: Client
    let selectedPrimitive: SearchRootModel.Pivot?
    let scopedShowIDs: [Int]
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

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
                    scopedShowIDs: scopedShowIDs
                )
            }

            if includes(.comedians) {
                SavedFavoritesSection(apiClient: apiClient)
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

    private func includes(_ primitive: SearchRootModel.Pivot) -> Bool {
        LibraryFavoritesPresentation.includes(primitive, selectedPrimitive: selectedPrimitive)
    }
}

private struct FavoriteShowsSection: View {
    let phase: LoadPhase<[Components.Schemas.Show]>
    /// Show ids from a notification tap; scopes the section to just those.
    var scopedShowIDs: [Int] = []

    @State private var showAll = false
    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>

    private var isScoped: Bool { !scopedShowIDs.isEmpty && !showAll }

    var body: some View {
        switch phase {
        case .success(let shows) where !shows.isEmpty:
            favoriteShowsContent(shows)
        default:
            EmptyView()
        }
    }

    private func favoriteShowsContent(_ shows: [Components.Schemas.Show]) -> some View {
        let scopedSet = Set(scopedShowIDs)
        let filtered = isScoped ? shows.filter { scopedSet.contains($0.id) } : Array(shows.prefix(4))
        return LaughTrackRailCard(
            eyebrow: "Favorites",
            title: isScoped ? "From your notification" : "Your favorites are touring",
            accessibilityIdentifier: LaughTrackViewTestID.favoritesShowsSection
        ) {
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                if isScoped {
                    Button {
                        showAll = true
                    } label: {
                        Text("Show all favorites")
                            .font(theme.laughTrackTokens.typography.metadata)
                            .foregroundColor(theme.colors.primary)
                    }
                    .buttonStyle(.plain)
                }

                ForEach(filtered, id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeFavoriteShowButton(show.id))
                }

                if isScoped, filtered.isEmpty {
                    Text("Those shows aren't in your upcoming favorites right now.")
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundColor(theme.colors.textSecondary)
                }
            }
        }
    }
}

enum LibraryFavoritesPresentation {
    static func includes(
        _ primitive: SearchRootModel.Pivot,
        selectedPrimitive: SearchRootModel.Pivot?
    ) -> Bool {
        guard primitive == .shows || primitive == .comedians else {
            return false
        }
        return selectedPrimitive == nil || selectedPrimitive == primitive
    }

    static func matches(show: Components.Schemas.Show, query: String) -> Bool {
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
    var body: some View {
        let tokens = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
            LaughTrackCard {
                VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                    ForEach(Self.sampleShows, id: \.0) { name, detail in
                        TeaserRow(title: name, subtitle: detail)
                    }
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

            LaughTrackInlineStateCard(
                tone: .empty,
                title: LibraryView.signedOutPromptTitle,
                message: "Open Profile to sign in. Your saved comedians and their upcoming shows follow your account."
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
    var systemImage: String? = nil
    var isPlaceholder = true

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        HStack(spacing: theme.spacing.sm) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(tokens.colors.textSecondary.opacity(0.15))
                if let systemImage {
                    Image(systemName: systemImage)
                        .foregroundStyle(tokens.colors.accent)
                }
            }
            .frame(width: 40, height: 40)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(tokens.typography.cardTitle)
                    .foregroundStyle(tokens.colors.textPrimary.opacity(isPlaceholder ? 0.6 : 1))
                    .redacted(reason: isPlaceholder ? .placeholder : [])
                Text(subtitle)
                    .font(tokens.typography.metadata)
                    .foregroundStyle(tokens.colors.textSecondary.opacity(isPlaceholder ? 0.6 : 1))
                    .redacted(reason: isPlaceholder ? .placeholder : [])
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
