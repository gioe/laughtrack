import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum LibrarySection: String, CaseIterable, Equatable {
    case nextUp
    case fromFollows
    case saved
    case history

    var title: String {
        switch self {
        case .nextUp: return "Next Up"
        case .fromFollows: return "From Your Follows"
        case .saved: return "Saved"
        case .history: return "History"
        }
    }
}

enum LibraryGroupResolution: Equatable {
    case loading
    case content
    case empty
    case failure
}

struct LibraryContentState: Equatable {
    let nextUp: LibraryGroupResolution
    let fromFollows: LibraryGroupResolution
    let saved: LibraryGroupResolution
    let history: LibraryGroupResolution

    var isFullyEmpty: Bool {
        [nextUp, fromFollows, saved, history].allSatisfy { $0 == .empty }
    }
}

@MainActor
enum LibrarySearchSeed {
    static let pivots: [SearchRootModel.Pivot] = [.shows, .comedians, .clubs, .podcasts]

    static func seed(for pivot: SearchRootModel.Pivot) -> SearchRootModel.Seed {
        SearchRootModel.Seed(
            pivot: pivot,
            query: "",
            shortcut: pivot == .shows ? "Near Me" : nil
        )
    }
}

@MainActor
struct LibraryView: View {
    static let title = "Library"
    static let signedOutPromptTitle = "Sign in to build your Library"

    let apiClient: Client
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
        selectedPrimitive _: SearchRootModel.Pivot? = nil,
        scopedShowIDs: [Int] = [],
        searchNavigationBridge: SearchNavigationBridge,
        screenshotPersona: AuthenticatedScreenshotPersona? = nil
    ) {
        self.apiClient = apiClient
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
                        scopedShowIDs: scopedShowIDs,
                        searchNavigationBridge: searchNavigationBridge,
                        savedShows: serviceContainer.resolve(SavedShowStore.self),
                        cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
                        persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
                    )
                } else {
                    LibraryEmptyState(
                        searchNavigationBridge: searchNavigationBridge,
                        requiresSignIn: true
                    )
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
            if !persona.upcomingSavedShows.isEmpty {
                screenshotSavedShowsSection(
                    section: .nextUp,
                    shows: persona.upcomingSavedShows
                )
            }

            if !persona.favoriteShows.isEmpty {
                TeaserSection(
                    eyebrow: "Following",
                    title: LibrarySection.fromFollows.title,
                    subtitle: "Upcoming shows from comedians you follow."
                ) {
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

            if !persona.favoriteComedians.isEmpty ||
                !persona.favoriteClubs.isEmpty ||
                !persona.favoritePodcasts.isEmpty {
                TeaserSection(
                    eyebrow: "Your collection",
                    title: LibrarySection.saved.title,
                    subtitle: "Comedians, clubs, and podcasts you want to keep close."
                ) {
                    VStack(alignment: .leading, spacing: tokens.spacing.tight) {
                        if !persona.favoriteComedians.isEmpty {
                            screenshotSavedGroupTitle("Comedians")
                        }
                        ForEach(persona.favoriteComedians, id: \.self) { name in
                            TeaserRow(
                                title: name,
                                subtitle: "Following · notifications on",
                                systemImage: "person.fill",
                                isPlaceholder: false
                            )
                        }
                        if !persona.favoriteClubs.isEmpty {
                            screenshotSavedGroupTitle("Clubs")
                        }
                        ForEach(persona.favoriteClubs, id: \.self) { name in
                            TeaserRow(
                                title: name,
                                subtitle: "Saved venue",
                                systemImage: "building.2.fill",
                                isPlaceholder: false
                            )
                        }
                        if !persona.favoritePodcasts.isEmpty {
                            screenshotSavedGroupTitle("Podcasts")
                        }
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

            if !persona.pastSavedShows.isEmpty {
                screenshotSavedShowsSection(
                    section: .history,
                    shows: persona.pastSavedShows
                )
            }
        }
    }

    private func screenshotSavedShowsSection(
        section: LibrarySection,
        shows: [(title: String, detail: String)]
    ) -> some View {
        TeaserSection(
            eyebrow: section == .nextUp ? "Plans" : "Past plans",
            title: section.title,
            subtitle: section == .nextUp
                ? "The shows you chose are always first."
                : "Past shows you saved."
        ) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.tight) {
                ForEach(shows, id: \.title) { show in
                    TeaserRow(
                        title: show.title,
                        subtitle: show.detail,
                        systemImage: "bookmark.fill",
                        isPlaceholder: false
                    )
                }
            }
        }
    }

    private func screenshotSavedGroupTitle(_ title: String) -> some View {
        Text(title.uppercased())
            .font(theme.laughTrackTokens.typography.eyebrow)
            .foregroundStyle(theme.colors.textSecondary)
            .padding(.top, theme.spacing.xs)
    }
}

private struct FavoritePrimitiveSections: View {
    let apiClient: Client
    let scopedShowIDs: [Int]
    let searchNavigationBridge: SearchNavigationBridge
    @ObservedObject var savedShows: SavedShowStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
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
            SavedShowsSection(
                section: .nextUp,
                period: .upcoming,
                phase: savedShows.upcomingPhase,
                shows: savedShows.upcomingPage?.shows ?? [],
                apiClient: apiClient,
                store: savedShows
            )

            FavoriteShowsSection(
                phase: favoriteShowsModel.phase,
                scopedShowIDs: scopedShowIDs
            )

            SavedFavoritesSection(apiClient: apiClient)

            SavedShowsSection(
                section: .history,
                period: .past,
                phase: savedShows.pastPhase,
                shows: savedShows.pastPage?.shows ?? [],
                apiClient: apiClient,
                store: savedShows
            )

            if contentState.isFullyEmpty {
                LibraryEmptyState(
                    searchNavigationBridge: searchNavigationBridge,
                    requiresSignIn: false
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
        .task {
            await savedShows.loadSavedShows(
                period: .upcoming,
                apiClient: apiClient,
                authManager: authManager
            )
            await savedShows.loadSavedShows(
                period: .past,
                apiClient: apiClient,
                authManager: authManager
            )
        }
    }

    @Environment(\.appTheme) private var theme

    private var themeSpacing: CGFloat {
        theme.laughTrackTokens.browseDensity.shelfGap
    }

    private var contentState: LibraryContentState {
        LibraryContentState(
            nextUp: resolution(
                phase: savedShows.upcomingPhase,
                hasContent: !(savedShows.upcomingPage?.shows.isEmpty ?? true)
            ),
            fromFollows: favoriteShowsResolution,
            saved: savedFavoritesResolution,
            history: resolution(
                phase: savedShows.pastPhase,
                hasContent: !(savedShows.pastPage?.shows.isEmpty ?? true)
            )
        )
    }

    private var favoriteShowsResolution: LibraryGroupResolution {
        switch favoriteShowsModel.phase {
        case .idle:
            return favorites.savedFavoritesPhase == .empty ? .empty : .loading
        case .loading:
            return .loading
        case .success(let shows):
            return shows.isEmpty ? .empty : .content
        case .failure:
            return .failure
        }
    }

    private var savedFavoritesResolution: LibraryGroupResolution {
        let hasContent = !favorites.savedFavoriteComedians.isEmpty ||
            !clubFavorites.savedFavoriteClubs.isEmpty ||
            !podcastFavorites.savedFavoritePodcasts.isEmpty
        if hasContent { return .content }

        let phasesAreEmpty = favorites.savedFavoritesPhase == .empty &&
            clubFavorites.savedFavoritesPhase == .empty &&
            podcastFavorites.savedFavoritesPhase == .empty
        if phasesAreEmpty { return .empty }

        let hasFailure = favorites.savedFavoritesPhase.hasFailure ||
            clubFavorites.savedFavoritesPhase.hasFailure ||
            podcastFavorites.savedFavoritesPhase.hasFailure
        return hasFailure ? .failure : .loading
    }

    private func resolution(
        phase: SavedShowStore.LoadPhase,
        hasContent: Bool
    ) -> LibraryGroupResolution {
        if hasContent { return .content }
        switch phase {
        case .idle, .loading: return .loading
        case .loaded, .empty: return .empty
        case .failure: return .failure
        }
    }
}

private struct SavedShowsSection: View {
    let section: LibrarySection
    let period: SavedShowStore.Period
    let phase: SavedShowStore.LoadPhase
    let shows: [Components.Schemas.Show]
    let apiClient: Client
    @ObservedObject var store: SavedShowStore

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    var body: some View {
        Group {
            if phase != .empty {
                LaughTrackRailCard(
                    eyebrow: section == .nextUp ? "Plans" : "Past plans",
                    title: section.title,
                    accessibilityIdentifier: "laughtrack.library.saved-shows-\(period.rawValue)"
                ) {
                    switch phase {
                    case .idle, .loading:
                        ShowsListSkeleton(rowCount: 2)
                    case .empty:
                        EmptyView()
                    case .failure(let failure):
                        VStack(alignment: .leading, spacing: theme.spacing.sm) {
                            LaughTrackStateView(
                                tone: .error,
                                title: "Couldn’t load \(section.title.lowercased())",
                                message: failure.message
                            )
                            LaughTrackButton(
                                "Retry \(section.title.lowercased())",
                                systemImage: "arrow.clockwise"
                            ) {
                                Task {
                                    await store.loadSavedShows(
                                        period: period,
                                        apiClient: apiClient,
                                        authManager: authManager,
                                        force: true
                                    )
                                }
                            }
                        }
                    case .loaded:
                        VStack(alignment: .leading, spacing: theme.spacing.sm) {
                            ForEach(shows, id: \.id) { show in
                                Button {
                                    coordinator.open(.show(show.id))
                                } label: {
                                    ShowRow(show: show, presentation: .compactTicket)
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("Open \(ShowTitlePresentation.title(for: show))")
                            }
                        }
                    }
                }
            }
        }
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
            eyebrow: "Following",
            title: isScoped ? "From Your Notification" : LibrarySection.fromFollows.title,
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

private struct LibraryEmptyState: View {
    let searchNavigationBridge: SearchNavigationBridge
    let requiresSignIn: Bool

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        LaughTrackRailCard(
            eyebrow: "Make it yours",
            title: requiresSignIn ? LibraryView.signedOutPromptTitle : "Start your Library",
            accessibilityIdentifier: "laughtrack.library.empty-state"
        ) {
            VStack(alignment: .leading, spacing: tokens.spacing.itemGap) {
                Text(emptyMessage)
                    .font(tokens.typography.body)
                    .foregroundStyle(tokens.colors.textSecondary)

                LazyVGrid(
                    columns: [GridItem(.adaptive(minimum: 145), spacing: theme.spacing.sm)],
                    alignment: .leading,
                    spacing: theme.spacing.sm
                ) {
                    searchButton("Shows near me", systemImage: "location.fill", pivot: .shows)
                    searchButton("Follow comedians", systemImage: "person.2.fill", pivot: .comedians)
                    searchButton("Save clubs", systemImage: "building.2.fill", pivot: .clubs)
                    searchButton("Save podcasts", systemImage: "mic.fill", pivot: .podcasts)
                }
            }
        }
    }

    private var emptyMessage: String {
        if requiresSignIn {
            return "Explore now, then sign in from Profile to keep plans and follows with your account."
        }
        return "Save a show or follow a comedian, club, or podcast. Your plans and favorites will collect here."
    }

    private func searchButton(
        _ title: String,
        systemImage: String,
        pivot: SearchRootModel.Pivot
    ) -> some View {
        LaughTrackButton(
            title,
            systemImage: systemImage,
            tone: .secondary,
            density: .compact
        ) {
            searchNavigationBridge.openSearch(LibrarySearchSeed.seed(for: pivot))
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

private extension ComedianFavoriteStore.SavedFavoritesPhase {
    var hasFailure: Bool {
        if case .failure = self { return true }
        return false
    }
}

private extension ClubFavoriteStore.SavedFavoritesPhase {
    var hasFailure: Bool {
        if case .failure = self { return true }
        return false
    }
}

private extension PodcastFavoriteStore.SavedFavoritesPhase {
    var hasFailure: Bool {
        if case .failure = self { return true }
        return false
    }
}
