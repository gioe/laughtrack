import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum HomeContentSection: Equatable {
    case showsTonight
    case moreNearYou
    case trendingThisWeek
    case favoriteShows
    case comedians
    case clubs
    case podcasts

    static func sections(for primitive: SearchRootModel.Pivot?) -> [HomeContentSection] {
        switch primitive {
        case .shows:
            return [.showsTonight, .moreNearYou, .trendingThisWeek, .favoriteShows]
        case .comedians:
            return [.comedians]
        case .clubs:
            return [.clubs]
        case .podcasts:
            return [.podcasts]
        default:
            return [.showsTonight, .moreNearYou, .trendingThisWeek, .favoriteShows, .comedians, .clubs, .podcasts]
        }
    }
}

enum HomeShowRailKind: Equatable {
    case showsTonight
    case moreNearYou
    case trendingThisWeek

    var eyebrow: String {
        switch self {
        case .showsTonight:
            return "Tonight"
        case .moreNearYou:
            return "More near you"
        case .trendingThisWeek:
            return "Trending this week"
        }
    }

    func title(cityTitle: String?) -> String {
        switch self {
        case .showsTonight:
            if let cityTitle {
                return "Shows tonight near \(cityTitle)"
            }
            return "Shows tonight"
        case .moreNearYou:
            return "More near you"
        case .trendingThisWeek:
            return "Trending this week"
        }
    }

    var subtitle: String? {
        switch self {
        case .showsTonight:
            return nil
        case .moreNearYou:
            return "Upcoming shows at clubs in your area."
        case .trendingThisWeek:
            return "The most popular shows happening in the next 7 days."
        }
    }

    var emptyMessage: String {
        switch self {
        case .showsTonight:
            return "No shows are listed for tonight yet."
        case .moreNearYou:
            return "No nearby shows are listed yet."
        case .trendingThisWeek:
            return "No trending shows are listed for this week yet."
        }
    }

    var searchShortcut: String? {
        switch self {
        case .showsTonight:
            return "Tonight"
        case .moreNearYou:
            return "Near Me"
        case .trendingThisWeek:
            return "This Week"
        }
    }

    var railAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightRail
        case .moreNearYou:
            return "laughtrack.home.more-near-you-rail"
        case .trendingThisWeek:
            return "laughtrack.home.trending-this-week-rail"
        }
    }

    var seeMoreAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightSeeMoreButton
        case .moreNearYou:
            return "laughtrack.home.more-near-you-see-more-button"
        case .trendingThisWeek:
            return "laughtrack.home.trending-this-week-see-more-button"
        }
    }
}

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let selectedPrimitive: SearchRootModel.Pivot?
    let searchNavigationBridge: SearchNavigationBridge

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        signedOutMessage: String?,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                HomeNearMeHeader(
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self)
                )

                contentSections
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, -4)
            .padding(.bottom, laughTrack.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.homeScreen)
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .background(
            laughTrack.gradients.heroWash
                .frame(maxHeight: 280)
                .ignoresSafeArea(edges: .top),
            alignment: .top
        )
        .navigationTitle("LaughTrack")
        .toolbar {
            ToolbarItem(placement: toolbarPlacement) {
                Button {
                    coordinator.push(AppRoute.nearMeToolbarTarget(isSignedIn: authManager.currentSession != nil))
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "person.crop.circle")
                }
                .accessibilityLabel(authManager.currentSession == nil ? "Sign in" : "Profile")
                .accessibilityIdentifier(LaughTrackViewTestID.homeSettingsButton)
            }
        }
        .modifier(LaughTrackNavigationChrome(background: laughTrack.colors.canvas))
    }

    private var toolbarPlacement: ToolbarItemPlacement {
        #if os(iOS)
        .topBarTrailing
        #else
        .primaryAction
        #endif
    }

    @ViewBuilder
    private var contentSections: some View {
        ForEach(HomeContentSection.sections(for: selectedPrimitive), id: \.self) { section in
            switch section {
            case .showsTonight:
                showsSection(.showsTonight)
            case .moreNearYou:
                showsSection(.moreNearYou)
            case .trendingThisWeek:
                showsSection(.trendingThisWeek)
            case .favoriteShows:
                HomeFavoriteShowsRail(
                    apiClient: apiClient,
                    cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
                    persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
                )
            case .comedians:
                comediansSection
            case .clubs:
                clubsSection
            case .podcasts:
                podcastsSection
            }
        }
    }

    private func showsSection(_ railKind: HomeShowRailKind) -> some View {
        HomeShowsTonightRail(
            railKind: railKind,
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var comediansSection: some View {
        HomeTrendingComediansRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var clubsSection: some View {
        HomePopularClubsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var podcastsSection: some View {
        HomeTrendingPodcastsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }
}

private struct HomeNearMeHeader: View {
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text("Discover")
                .font(laughTrack.typography.sectionTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(1)
                .minimumScaleFactor(0.85)

            Text(subtitle)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(LaughTrackViewTestID.homeNearMeHeader)
    }

    private var subtitle: String {
        guard let preference = nearbyPreferenceStore.preference else {
            return "Shows, comedians, clubs, and podcasts handpicked for you."
        }

        let source = preference.source == .manual ? "saved ZIP" : "current location"
        return "Using your \(source): \(preference.zipCode) within \(preference.distanceMiles) mi."
    }
}

private struct HomeShowsTonightRail: View {
    let railKind: HomeShowRailKind
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model = HomeShowsTonightModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: railKind.eyebrow,
                title: title,
                subtitle: railKind.subtitle
            )
            // Anchoring the rail's test identifier on the shelf header — not the
            // outer VStack — keeps it from propagating to the combined-children
            // accessibility nodes produced by the hero/rail cards under iOS 26,
            // which would otherwise mask the inner Button identifiers.
            .accessibilityIdentifier(railKind.railAccessibilityIdentifier)

            switch model.phase {
            case .idle, .loading:
                ShowsListSkeleton(rowCount: 3)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            railKind: railKind,
                            apiClient: apiClient,
                            zipCode: zipCode,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let shows):
                if shows.isEmpty {
                    EmptyCard(message: railKind.emptyMessage)
                } else {
                    showsContent(shows)
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, railKind: railKind)) {
            await model.refresh(
                railKind: railKind,
                apiClient: apiClient,
                zipCode: zipCode,
                cache: cache,
                persistentCache: persistentCache
            )
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var title: String {
        railKind.title(cityTitle: model.cityTitle)
    }

    @ViewBuilder
    private func showsContent(_ shows: [Components.Schemas.Show]) -> some View {
        if railKind == .showsTonight {
            HomeShowsTonightCarousel(shows: shows)
        } else {
            VStack(spacing: theme.spacing.sm) {
                ForEach(shows, id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightButton(show.id))
                }
            }
        }

        LaughTrackButton("See more", systemImage: "magnifyingglass", tone: .secondary, density: .compact) {
            searchNavigationBridge.openSearch(
                HomeShowsTonightModel.seeMoreSearchSeed(
                    railKind: railKind,
                    nearbyPreference: seeMoreNearbyPreference
                )
            )
        }
        .accessibilityIdentifier(railKind.seeMoreAccessibilityIdentifier)
    }

    private var seeMoreNearbyPreference: NearbyPreference? {
        nearbyPreferenceStore.preference ?? model.feedNearbyPreference
    }
}

private struct HomeShowsTonightCarousel: View {
    let shows: [Components.Schemas.Show]

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme
    @State private var selectedShowID: Int?

    var body: some View {
        #if os(iOS)
        VStack(spacing: theme.spacing.xs) {
            TabView(selection: selectedShowIDBinding) {
                carouselButtons
            }
            .frame(height: 292)
            .tabViewStyle(PageTabViewStyle(indexDisplayMode: .never))

            HomeShowsTonightPageIndicator(
                count: shows.count,
                selectedIndex: selectedShowIndex
            )
        }
        #else
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                carouselButtons
                    .frame(width: 320)
            }
        }
        #endif
    }

    private var carouselButtons: some View {
        ForEach(shows, id: \.id) { show in
            Button {
                coordinator.open(.show(show.id))
            } label: {
                HomeShowsTonightHeroCard(show: show)
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier(show.id == shows.first?.id ? LaughTrackViewTestID.homeShowsTonightHeroButton : LaughTrackViewTestID.homeShowsTonightButton(show.id))
            .padding(.horizontal, 1)
            .tag(show.id)
        }
    }

    private var selectedShowIDBinding: Binding<Int> {
        Binding(
            get: { selectedShowID ?? shows.first?.id ?? 0 },
            set: { selectedShowID = $0 }
        )
    }

    private var selectedShowIndex: Int {
        guard let selectedID = selectedShowID ?? shows.first?.id,
              let index = shows.firstIndex(where: { $0.id == selectedID })
        else {
            return 0
        }

        return index
    }
}

private struct HomeShowsTonightPageIndicator: View {
    let count: Int
    let selectedIndex: Int

    @Environment(\.appTheme) private var theme

    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<count, id: \.self) { index in
                Circle()
                    .fill(
                        index == selectedIndex
                            ? theme.laughTrackTokens.colors.textPrimary
                            : theme.laughTrackTokens.colors.textSecondary.opacity(0.45)
                    )
                    .frame(width: 7, height: 7)
            }
        }
        .frame(height: count > 1 ? 12 : 0)
        .opacity(count > 1 ? 1 : 0)
        .accessibilityHidden(true)
    }
}

private struct HomeShowsTonightHeroCard: View {
    let show: Components.Schemas.Show

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            artwork

            VStack(alignment: .leading, spacing: theme.spacing.xs) {
                Text(ShowTitlePresentation.title(for: show))
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)

                Text(show.clubName ?? "Unknown club")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)

                Text(metadata.joined(separator: " • "))
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
            }

            if HomeShowsTonightHeroPresentation.shouldShowFooter(for: show) {
                EmptyView()
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surface)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(ShowTitlePresentation.title(for: show)), \(show.clubName ?? "Unknown club"), \(metadata.joined(separator: ", "))")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(show.imageUrl) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
            .frame(maxWidth: .infinity)
            .frame(height: 144)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        } else {
            fallbackArtwork
                .frame(maxWidth: .infinity)
                .frame(height: 144)
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 16, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "ticket.fill")
                    .font(.system(size: 30, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    private var metadata: [String] {
        [
            ShowFormatting.listDate(show.date, timezoneID: show.timezone),
            show.room,
            ShowRow.priceLabel(for: show),
        ].compactMap { value in
            guard let value, !value.isEmpty else { return nil }
            return value
        }
    }

}

enum HomeShowsTonightHeroPresentation {
    static func shouldShowFooter(for show: Components.Schemas.Show) -> Bool {
        false
    }
}

@MainActor
final class HomeShowsTonightModel: ObservableObject {
    static let displayLimit = 5

    static func seeMoreSearchSeed(
        railKind: HomeShowRailKind,
        nearbyPreference: NearbyPreference?
    ) -> SearchRootModel.Seed {
        SearchRootModel.Seed(
            pivot: .shows,
            query: "",
            shortcut: railKind.searchShortcut,
            nearbyPreference: nearbyPreference
        )
    }

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle
    @Published private(set) var cityTitle: String?
    @Published private(set) var feedNearbyPreference: NearbyPreference?

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, railKind: HomeShowRailKind? = nil) -> String {
        "\(railKind.map(String.init(describing:)) ?? "showsTonight")|\(zipCode ?? "")"
    }

    func refresh(
        railKind: HomeShowRailKind = .showsTonight,
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = requestKey(for: zipCode, railKind: railKind)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, railKind: railKind, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load tonight's shows.",
            rateLimitMessage: "LaughTrack is rate-limiting tonight's shows right now.",
            undocumentedContext: "tonight's shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the home feed. Check your connection and try again.",
            persistentCache: persistentCache
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, railKind: railKind, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind, requestKey: String) {
        cityTitle = Self.locationTitle(city: feed.hero.city, state: feed.hero.state)
        feedNearbyPreference = Self.nearbyPreference(from: feed.hero)
        phase = .success(Self.shows(from: feed, railKind: railKind))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private static func shows(from feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind) -> [Components.Schemas.Show] {
        let sourceShows: [Components.Schemas.Show]
        switch railKind {
        case .showsTonight:
            sourceShows = feed.showsTonight + feed.hero.shows + feed.trendingThisWeek
        case .moreNearYou:
            sourceShows = feed.moreNearYou + feed.hero.shows + feed.showsTonight
        case .trendingThisWeek:
            sourceShows = feed.trendingThisWeek + feed.showsTonight + feed.moreNearYou
        }

        var seenIDs: Set<Int> = []
        return sourceShows.filter { show in
            seenIDs.insert(show.id).inserted
        }.prefix(Self.displayLimit).map { $0 }
    }

    private static func locationTitle(city: String?, state: String?) -> String? {
        guard let city, !city.isEmpty else { return nil }
        if let state, !state.isEmpty {
            return "\(city), \(state)"
        }
        return city
    }

    private static func nearbyPreference(from hero: Components.Schemas.HomeFeedHero) -> NearbyPreference? {
        guard let zipCode = hero.zipCode?.filter(\.isNumber), zipCode.count == 5 else {
            return nil
        }

        return NearbyPreference(
            zipCode: zipCode,
            source: .manual,
            distanceMiles: NearbyPreference.defaultDistanceMiles,
            city: hero.city,
            state: hero.state
        )
    }
}

private struct HomeFavoriteShowsRail: View {
    let apiClient: Client
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @StateObject private var model = HomeFavoriteShowsModel()

    private var favoriteComedians: [Components.Schemas.ComedianSearchItem] {
        guard favorites.savedFavoritesPhase == .loaded else { return [] }

        return favorites.savedFavoriteComedians
    }

    private var requestKey: String {
        favoriteComedians.map(\.uuid).joined(separator: "|")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            switch model.phase {
            case .success(let shows) where !shows.isEmpty:
                favoriteShowsContent(shows)
            default:
                EmptyView()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .task(id: requestKey) {
            await model.refresh(
                apiClient: apiClient,
                favoriteComedians: favoriteComedians,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private func favoriteShowsContent(_ shows: [Components.Schemas.Show]) -> some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Favorites",
                title: "Your favorites are touring",
                subtitle: "Upcoming after tonight from comedians you saved."
            )

            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                ForEach(shows.prefix(4), id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeFavoriteShowButton(show.id))
                }
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .accessibilityIdentifier(LaughTrackViewTestID.homeFavoriteShowsRail)
    }
}

@MainActor
final class HomeFavoriteShowsModel: ObservableObject {
    private static let maxFavoriteQueries = 5
    private static let showsPerFavorite = 3

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func refresh(
        apiClient: Client,
        favoriteComedians: [Components.Schemas.ComedianSearchItem],
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = Self.requestKey(for: favoriteComedians)
        guard !requestKey.isEmpty else {
            loadedRequestKey = nil
            loadedAt = nil
            phase = .idle
            return
        }
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedShows: [Components.Schemas.Show] = await MainPageCache.get(
            .favoriteShows(requestKey: requestKey),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(shows: cachedShows, requestKey: requestKey)
            return
        }

        phase = .loading

        var showsByID: [Int: Components.Schemas.Show] = [:]

        for comedian in favoriteComedians.prefix(Self.maxFavoriteQueries) {
            do {
                let output = try await apiClient.searchShows(
                    .init(
                        query: .init(
                            from: ShowFormatting.apiDate(Date()),
                            page: 0,
                            size: Self.showsPerFavorite,
                            comedian: comedian.name,
                            sort: ShowSortOption.earliest.rawValue
                        ),
                        headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                    )
                )

                guard case .ok(let ok) = output else { continue }
                let response = try ok.body.json
                for show in response.data where Self.show(show, matches: comedian) {
                    showsByID[show.id] = show
                }
            } catch {
                guard !Task.isCancelled else { return }
                continue
            }
        }

        let shows = showsByID.values.sorted { $0.date < $1.date }
        await MainPageCache.set(
            shows,
            forKey: .favoriteShows(requestKey: requestKey),
            in: cache,
            ttl: cacheTTL,
            persistentCache: persistentCache
        )
        apply(shows: shows, requestKey: requestKey)
    }

    private func apply(shows: [Components.Schemas.Show], requestKey: String) {
        phase = .success(shows)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func requestKey(for favoriteComedians: [Components.Schemas.ComedianSearchItem]) -> String {
        favoriteComedians.map(\.uuid).joined(separator: "|")
    }

    static func show(
        _ show: Components.Schemas.Show,
        matches favorite: Components.Schemas.ComedianSearchItem
    ) -> Bool {
        guard let lineup = show.lineup, !lineup.isEmpty else { return true }
        return lineup.contains { comedian in
            comedian.uuid == favorite.uuid ||
                comedian.id == favorite.id ||
                comedian.name.localizedCaseInsensitiveCompare(favorite.name) == .orderedSame
        }
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

private struct HomeTrendingComediansRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingComediansModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Comics on the rise this week",
                title: "Comedians drawing crowds",
                subtitle: nil
            )
            // Anchoring the rail's test identifier on the shelf header — not the
            // inner VStack — keeps it from propagating to the combined-children
            // accessibility nodes produced by HomeTrendingComedianCard under
            // iOS 26, which would otherwise mask the inner Button identifiers.
            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingComediansRail)

            switch model.phase {
            case .idle, .loading:
                ComediansListSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let items):
                if items.isEmpty {
                    EmptyCard(message: "No trending comedians with photos are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(items, id: \.uuid) { comedian in
                            Button {
                                coordinator.open(.comedian(comedian.id))
                            } label: {
                                HomeTrendingComedianCard(comedian: comedian)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingComedianButton(comedian.id))
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                cache: cache,
                persistentCache: persistentCache
            )
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomeTrendingComedianCard: View {
    let comedian: Components.Schemas.ComedianListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            VStack(alignment: .leading, spacing: 3) {
                Text(comedian.name)
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Text(upcomingShowsText)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(comedian.name), \(upcomingShowsText)")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        Image(systemName: "photo")
                            .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 112)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        } else {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
                .overlay {
                    Image(systemName: "music.mic")
                        .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.accentStrong)
                }
                .frame(maxWidth: .infinity)
                .frame(height: 112)
        }
    }

    private var upcomingShowsText: String {
        "\(comedian.showCount) show\(comedian.showCount == 1 ? "" : "s") upcoming"
    }
}

@MainActor
final class HomeTrendingComediansModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ComedianListItem]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?) -> String {
        zipCode ?? ""
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending comedians.",
            rateLimitMessage: "LaughTrack is rate-limiting trending comedians right now.",
            undocumentedContext: "trending comedians",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending comedians service. Check your connection and try again.",
            persistentCache: persistentCache
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(Self.railItems(from: feed.trendingComedians))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func railItems(
        from comedians: [Components.Schemas.ComedianListItem]
    ) -> [Components.Schemas.ComedianListItem] {
        let photoBacked = comedians.filter(hasUsablePhoto)
        guard photoBacked.count >= 10 else {
            return photoBacked
        }

        let noPhoto = comedians.filter { !hasUsablePhoto($0) }
        return photoBacked + noPhoto
    }

    private static func hasUsablePhoto(_ comedian: Components.Schemas.ComedianListItem) -> Bool {
        let rawValue = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return URL.normalizedExternalURL(rawValue) != nil
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

private struct HomePopularClubsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model = HomePopularClubsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Popular local clubs",
                title: "Go where the crowds are",
                subtitle: nil
            )
            // Anchoring the rail's test identifier on the shelf header — not the
            // inner VStack — keeps it from propagating to the combined-children
            // accessibility nodes produced by HomePopularClubCard under iOS 26,
            // which would otherwise mask the inner Button identifiers.
            .accessibilityIdentifier(LaughTrackViewTestID.homePopularClubsRail)

            switch model.phase {
            case .idle, .loading:
                ClubsListSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let clubs):
                if clubs.isEmpty {
                    EmptyCard(message: "No clubs are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(clubs, id: \.id) { club in
                            Button {
                                coordinator.open(.club(club.id))
                            } label: {
                                HomePopularClubCard(club: club)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                cache: cache,
                persistentCache: persistentCache
            )
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomePopularClubCard: View {
    let club: Components.Schemas.ClubListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            Text(club.name)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 150, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(club.name)
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
            .frame(maxWidth: .infinity)
            .frame(height: 104)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "building.2.fill")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 104)
    }

}

@MainActor
final class HomePopularClubsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ClubListItem]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?) -> String {
        zipCode ?? ""
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load clubs.",
            rateLimitMessage: "LaughTrack is rate-limiting clubs right now.",
            undocumentedContext: "clubs",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the clubs service. Check your connection and try again.",
            persistentCache: persistentCache
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(feed.popularClubs)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

enum MainPageCache {
    static let defaultTTL: TimeInterval = 60 * 60

    static func get<Value>(
        _ key: LaughTrackCacheKey,
        from cache: DataCache<LaughTrackCacheKey>?,
        persistentCache: PersistentMainPageCache?
    ) async -> Value? {
        if let cached: Value = await cache?.get(forKey: key) {
            return cached
        }

        guard let persistentCache else {
            return nil
        }

        switch key {
        case .homeFeed(let zipCode) where Value.self == Components.Schemas.HomeFeed.self:
            guard let cached = await persistentCache.getCachedHomeFeed(zipCode: zipCode) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        case .favoriteShows(let requestKey) where Value.self == [Components.Schemas.Show].self:
            guard let cached = await persistentCache.getCachedFavoriteShows(requestKey: requestKey) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        default:
            return nil
        }
    }

    static func set(
        _ value: some Sendable,
        forKey key: LaughTrackCacheKey,
        in cache: DataCache<LaughTrackCacheKey>?,
        ttl: TimeInterval = defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        await cache?.set(value, forKey: key, ttl: ttl)

        switch key {
        case .homeFeed(let zipCode):
            guard let homeFeed = value as? Components.Schemas.HomeFeed else { return }
            await persistentCache?.setHomeFeed(homeFeed, zipCode: zipCode, ttl: ttl)
        case .favoriteShows(let requestKey):
            guard let shows = value as? [Components.Schemas.Show] else { return }
            await persistentCache?.setFavoriteShows(shows, requestKey: requestKey, ttl: ttl)
        default:
            return
        }
    }

    private static func hydrateMemoryCache(
        _ value: some Sendable,
        key: LaughTrackCacheKey,
        expiresAt: Date,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        await cache?.set(value, forKey: key, ttl: max(0, expiresAt.timeIntervalSinceNow))
    }
}

private enum HomeFeedRequest {
    static func load(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        do {
            let output = try await apiClient.getHomeFeed(
                .init(
                    query: .init(zip: zipCode),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                await MainPageCache.set(
                    response.data,
                    forKey: .homeFeed(zipCode: zipCode),
                    in: cache,
                    ttl: cacheTTL,
                    persistentCache: persistentCache
                )
                return .success(response.data)
            case .badRequest(let badRequest):
                return .failure(
                    .badParams((try? badRequest.body.json.error) ?? badParamsMessage)
                )
            case .tooManyRequests(let tooManyRequests):
                return .failure(
                    .rateLimited(retryAfter: nil, message: (try? tooManyRequests.body.json.error) ?? rateLimitMessage)
                )
            case .internalServerError(let serverError):
                return .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: undocumentedContext))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: networkContext,
                networkMessage: networkMessage
            ))
        }
    }
}

struct HomeTrendingPodcastsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingPodcastsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Podcasts worth a listen",
                title: "Trending comedian podcasts",
                subtitle: nil
            )
            // Anchoring the rail's test identifier on the shelf header — not the
            // inner VStack — keeps it from propagating to the combined-children
            // accessibility nodes produced by HomeTrendingPodcastCard under
            // iOS 26, which would otherwise mask the inner Button identifiers.
            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingPodcastsRail)

            switch model.phase {
            case .idle, .loading:
                PodcastsListSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let items):
                if items.isEmpty {
                    EmptyCard(message: "No trending podcasts are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(items, id: \.id) { podcast in
                            Button {
                                coordinator.open(.podcast(podcast.id))
                            } label: {
                                HomeTrendingPodcastCard(podcast: podcast)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingPodcastButton(podcast.id))
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                cache: cache,
                persistentCache: persistentCache
            )
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomeTrendingPodcastCard: View {
    let podcast: Components.Schemas.HomeFeedPodcast

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            VStack(alignment: .leading, spacing: 3) {
                Text(podcast.title)
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Text(subtitleText)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(podcast.title), \(subtitleText)")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = podcast.imageUrl?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let raw = trimmed, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
            .frame(maxWidth: .infinity)
            .frame(height: 112)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "headphones")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 112)
    }

    private var subtitleText: String {
        if let author = podcast.authorName?.trimmingCharacters(in: .whitespacesAndNewlines), !author.isEmpty {
            return author
        }
        let count = podcast.episodeCount
        return "\(count) episode\(count == 1 ? "" : "s")"
    }
}

@MainActor
final class HomeTrendingPodcastsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.HomeFeedPodcast]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?) -> String {
        zipCode ?? ""
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending podcasts.",
            rateLimitMessage: "LaughTrack is rate-limiting trending podcasts right now.",
            undocumentedContext: "trending podcasts",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending podcasts service. Check your connection and try again.",
            persistentCache: persistentCache
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(feed.trendingPodcasts)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
