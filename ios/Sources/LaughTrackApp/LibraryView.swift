import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum LibrarySection: String, CaseIterable, Equatable {
    case nextUp
    case comedians
    case clubs
    case podcasts

    var title: String {
        switch self {
        case .nextUp: return "Shows"
        case .comedians: return "Comedians"
        case .clubs: return "Clubs"
        case .podcasts: return "Podcasts"
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
    let comedians: LibraryGroupResolution
    let clubs: LibraryGroupResolution
    let podcasts: LibraryGroupResolution

    var isFullyEmpty: Bool {
        [nextUp, comedians, clubs, podcasts].allSatisfy { $0 == .empty }
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
        searchNavigationBridge: SearchNavigationBridge,
        screenshotPersona: AuthenticatedScreenshotPersona? = nil
    ) {
        self.apiClient = apiClient
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
                        searchNavigationBridge: searchNavigationBridge,
                        savedShows: serviceContainer.resolve(SavedShowStore.self)
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
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var savedShowsPage = 0
    @State private var favoriteComediansPage = 0
    @State private var favoriteClubsPage = 0
    @State private var favoritePodcastsPage = 0

    private let pageSize = 5

    var body: some View {
        let tokens = theme.laughTrackTokens
        VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
            if !persona.upcomingSavedShows.isEmpty {
                screenshotSavedShowsSection(
                    section: .nextUp,
                    shows: persona.upcomingSavedShows
                )
            }

            if !persona.favoriteComedians.isEmpty {
                screenshotSavedEntitySection(
                    section: .comedians,
                    items: persona.favoriteComedians,
                    page: $favoriteComediansPage,
                    subtitle: "Following · notifications on",
                    kind: .comedian,
                    destination: { .comedian(101 + $0) }
                )
            }

            if !persona.favoriteClubs.isEmpty {
                screenshotSavedEntitySection(
                    section: .clubs,
                    items: persona.favoriteClubs,
                    page: $favoriteClubsPage,
                    subtitle: "Saved venue",
                    kind: .club,
                    destination: { .club(201 + $0) }
                )
            }

            if !persona.favoritePodcasts.isEmpty {
                screenshotSavedEntitySection(
                    section: .podcasts,
                    items: persona.favoritePodcasts,
                    page: $favoritePodcastsPage,
                    subtitle: "Vulture · 248 episodes",
                    kind: .podcast,
                    destination: { .podcast(301 + $0) }
                )
            }

        }
    }

    private func screenshotSavedShowsSection(
        section: LibrarySection,
        shows: [Components.Schemas.Show]
    ) -> some View {
        let pageCount = max(1, Int(ceil(Double(shows.count) / Double(pageSize))))
        let clampedPage = min(savedShowsPage, pageCount - 1)
        let start = clampedPage * pageSize
        let visibleShows = Array(shows[start..<min(start + pageSize, shows.count)])

        return LaughTrackRailCard(title: section.title) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.tight) {
                ForEach(visibleShows, id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show, presentation: .compactTicket)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Open \(ShowTitlePresentation.title(for: show))")
                }

                if pageCount > 1 {
                    LaughTrackPagedControls(
                        currentPage: clampedPage,
                        pageCount: pageCount,
                        onPrevious: { savedShowsPage = max(0, clampedPage - 1) },
                        onNext: { savedShowsPage = min(pageCount - 1, clampedPage + 1) }
                    )
                }
            }
        }
    }

    // TASK-3933 upgrades the deterministic screenshot fixture from lightweight
    // tuples to real Shows. Keep the Library redesign compatible with both
    // shapes so the two tasks can land independently.
    private func screenshotSavedShowsSection(
        section: LibrarySection,
        shows: [(title: String, detail: String)]
    ) -> some View {
        let pageCount = max(1, Int(ceil(Double(shows.count) / Double(pageSize))))
        let clampedPage = min(savedShowsPage, pageCount - 1)
        let start = clampedPage * pageSize
        let visibleShows = Array(shows[start..<min(start + pageSize, shows.count)])

        return LaughTrackRailCard(title: section.title) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.tight) {
                ForEach(Array(visibleShows.enumerated()), id: \.offset) { _, show in
                    TeaserRow(
                        title: show.title,
                        subtitle: show.detail,
                        systemImage: "ticket",
                        isPlaceholder: false
                    )
                }

                if pageCount > 1 {
                    LaughTrackPagedControls(
                        currentPage: clampedPage,
                        pageCount: pageCount,
                        onPrevious: { savedShowsPage = max(0, clampedPage - 1) },
                        onNext: { savedShowsPage = min(pageCount - 1, clampedPage + 1) }
                    )
                }
            }
        }
    }

    private func screenshotSavedEntitySection(
        section: LibrarySection,
        items: [String],
        page: Binding<Int>,
        subtitle: String,
        kind: LaughTrackSearchEntityKind,
        destination: @escaping (Int) -> EntityNavigationTarget
    ) -> some View {
        let pageCount = max(1, Int(ceil(Double(items.count) / Double(pageSize))))
        let clampedPage = min(page.wrappedValue, pageCount - 1)
        let start = clampedPage * pageSize
        let visibleItems = Array(items.enumerated())[start..<min(start + pageSize, items.count)]

        return LaughTrackRailCard(title: section.title) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.tight) {
                ForEach(Array(visibleItems), id: \.offset) { index, name in
                    LaughTrackSearchEntityRow(
                        title: name,
                        subtitle: subtitle,
                        imageURL: nil,
                        kind: kind,
                        action: { coordinator.open(destination(index)) },
                        accessibilityIdentifier: "laughtrack.library.fixture-\(section.rawValue)-\(index)"
                    )
                }

                if pageCount > 1 {
                    LaughTrackPagedControls(
                        currentPage: clampedPage,
                        pageCount: pageCount,
                        onPrevious: { page.wrappedValue = max(0, clampedPage - 1) },
                        onNext: { page.wrappedValue = min(pageCount - 1, clampedPage + 1) }
                    )
                }
            }
        }
    }

}

private struct FavoritePrimitiveSections: View {
    let apiClient: Client
    let searchNavigationBridge: SearchNavigationBridge
    @ObservedObject var savedShows: SavedShowStore

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @EnvironmentObject private var clubFavorites: ClubFavoriteStore
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    var body: some View {
        VStack(alignment: .leading, spacing: themeSpacing) {
            SavedShowsSection(
                section: .nextUp,
                period: .upcoming,
                phase: savedShows.upcomingPhase,
                page: savedShows.upcomingPage,
                apiClient: apiClient,
                store: savedShows
            )

            SavedFavoritesSection(apiClient: apiClient)

            if contentState.isFullyEmpty {
                LibraryEmptyState(
                    searchNavigationBridge: searchNavigationBridge,
                    requiresSignIn: false
                )
            }
        }
        .task {
            await savedShows.loadSavedShows(
                period: .upcoming,
                size: SavedShowsSection.pageSize,
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
            comedians: comedianFavoritesResolution,
            clubs: clubFavoritesResolution,
            podcasts: podcastFavoritesResolution
        )
    }

    private var comedianFavoritesResolution: LibraryGroupResolution {
        if !favorites.savedFavoriteComedians.isEmpty { return .content }
        switch favorites.savedFavoritesPhase {
        case .idle, .loading: return .loading
        case .loaded, .empty: return .empty
        case .failure: return .failure
        }
    }

    private var clubFavoritesResolution: LibraryGroupResolution {
        if !clubFavorites.savedFavoriteClubs.isEmpty { return .content }
        switch clubFavorites.savedFavoritesPhase {
        case .idle, .loading: return .loading
        case .loaded, .empty: return .empty
        case .failure: return .failure
        }
    }

    private var podcastFavoritesResolution: LibraryGroupResolution {
        if !podcastFavorites.savedFavoritePodcasts.isEmpty { return .content }
        switch podcastFavorites.savedFavoritesPhase {
        case .idle, .loading: return .loading
        case .loaded, .empty: return .empty
        case .failure: return .failure
        }
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
    static let pageSize = 5

    let section: LibrarySection
    let period: SavedShowStore.Period
    let phase: SavedShowStore.LoadPhase
    let page: SavedShowStore.Page?
    let apiClient: Client
    @ObservedObject var store: SavedShowStore
    @State private var displayedPage = 0

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    private var shows: [Components.Schemas.Show] { page?.shows ?? [] }

    private var pageCount: Int { max(1, page?.totalPages ?? 1) }

    private var clampedDisplayedPage: Int {
        min(displayedPage, max(0, pageCount - 1))
    }

    private var visibleShows: [Components.Schemas.Show] {
        let start = clampedDisplayedPage * Self.pageSize
        guard start < shows.count else { return [] }
        return Array(shows[start..<min(start + Self.pageSize, shows.count)])
    }

    var body: some View {
        Group {
            if phase != .empty {
                LaughTrackRailCard(
                    title: section.title,
                    accessibilityIdentifier: "laughtrack.library.saved-shows-\(period.rawValue)"
                ) {
                    if shows.isEmpty {
                        initialContent
                    } else {
                        loadedContent
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var initialContent: some View {
        switch phase {
        case .idle, .loading:
            ShowsListSkeleton(rowCount: 2)
        case .empty, .loaded:
            EmptyView()
        case .failure(let failure):
            failureContent(failure, loadingMore: false)
        }
    }

    private var loadedContent: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            ForEach(visibleShows, id: \.id) { show in
                Button {
                    coordinator.open(.show(show.id))
                } label: {
                    ShowRow(show: show, presentation: .compactTicket)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open \(ShowTitlePresentation.title(for: show))")
            }

            if pageCount > 1 {
                LaughTrackPagedControls(
                    currentPage: clampedDisplayedPage,
                    pageCount: pageCount,
                    onPrevious: showPreviousPage,
                    onNext: showNextPage
                )
                .disabled(phase == .loading)
            }

            if phase == .loading {
                ProgressView("Loading page…")
            } else if case .failure(let failure) = phase {
                failureContent(failure, loadingMore: true)
            }
        }
    }

    private func failureContent(
        _ failure: LoadFailure,
        loadingMore: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            LaughTrackStateView(
                tone: .error,
                title: loadingMore
                    ? "Couldn’t load more \(section.title.lowercased())"
                    : "Couldn’t load \(section.title.lowercased())",
                message: failure.message
            )
            LaughTrackButton(
                loadingMore
                    ? "Retry loading more"
                    : "Retry \(section.title.lowercased())",
                systemImage: "arrow.clockwise"
            ) {
                if loadingMore {
                    loadNextPage(force: true, displayAfterLoad: true)
                } else {
                    Task {
                        await store.loadSavedShows(
                            period: period,
                            size: Self.pageSize,
                            apiClient: apiClient,
                            authManager: authManager,
                            force: true
                        )
                    }
                }
            }
        }
    }

    private func showPreviousPage() {
        displayedPage = max(0, clampedDisplayedPage - 1)
    }

    private func showNextPage() {
        let targetPage = min(pageCount - 1, clampedDisplayedPage + 1)
        let highestLoadedPage = max(0, (page?.page ?? 1) - 1)
        if targetPage <= highestLoadedPage {
            displayedPage = targetPage
        } else {
            loadNextPage(displayAfterLoad: true)
        }
    }

    private func loadNextPage(
        force: Bool = false,
        displayAfterLoad: Bool = false
    ) {
        let pageBeforeLoad = page?.page ?? 0
        Task {
            await store.loadNextSavedShowsPage(
                period: period,
                size: Self.pageSize,
                apiClient: apiClient,
                authManager: authManager,
                force: force
            )
            let loadedPage = period == .upcoming ? store.upcomingPage : store.pastPage
            if displayAfterLoad, (loadedPage?.page ?? 0) > pageBeforeLoad {
                displayedPage = pageBeforeLoad
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
