import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let searchNavigationBridge: SearchNavigationBridge

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                HomeShowsTonightRail(
                    apiClient: apiClient,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
                )

                HomeFavoriteShowsRail(
                    apiClient: apiClient,
                    cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
                )

                HomeTrendingComediansRail(
                    apiClient: apiClient,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
                )

                HomeNearbyDiscoverySection(
                    apiClient: apiClient,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, laughTrack.browseDensity.heroPadding)
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
                    coordinator.push(AppRoute.homeToolbarTarget(isSignedIn: authManager.currentSession != nil))
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "gearshape")
                }
                .accessibilityLabel(authManager.currentSession == nil ? "Sign in" : "Settings")
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
}

private struct HomeShowsTonightRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>

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
                eyebrow: "Tonight",
                title: title,
                subtitle: nil
            )

            switch model.phase {
            case .idle, .loading:
                LoadingCard(title: "Loading tonight's shows")
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.refresh(apiClient: apiClient, zipCode: zipCode, cache: cache) },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let shows):
                if shows.isEmpty {
                    EmptyCard(message: "No shows are listed for tonight yet.")
                } else {
                    showsContent(shows)
                }
            }
        }
        .task(id: model.requestKey(for: zipCode)) {
            await model.refresh(apiClient: apiClient, zipCode: zipCode, cache: cache)
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightRail)
    }

    private var title: String {
        if let city = model.cityTitle {
            return "Shows tonight near \(city)"
        }
        return "Shows tonight"
    }

    @ViewBuilder
    private func showsContent(_ shows: [Components.Schemas.Show]) -> some View {
        if let heroShow = shows.first {
            Button {
                coordinator.open(.show(heroShow.id))
            } label: {
                HomeShowsTonightHeroCard(show: heroShow)
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightHeroButton)
        }

        let railShows = Array(shows.dropFirst().prefix(8))
        if !railShows.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(alignment: .top, spacing: theme.spacing.sm) {
                    ForEach(railShows, id: \.id) { show in
                        Button {
                            coordinator.open(.show(show.id))
                        } label: {
                            HomeShowsTonightRailCard(show: show)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightButton(show.id))
                    }
                }
                .padding(.horizontal, 1)
                .padding(.vertical, 2)
            }
        }
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
                Text(show.name ?? "Untitled show")
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

            HStack(spacing: theme.spacing.sm) {
                LaughTrackBadge(lineupPreview, systemImage: "person.2.fill", tone: .neutral)

                Spacer(minLength: theme.spacing.sm)

                HStack(spacing: theme.spacing.xs) {
                    Text(show.soldOut == true ? "Sold out" : "Tickets")
                    Image(systemName: "arrow.right")
                }
                .font(laughTrack.typography.metadata)
                .foregroundStyle(show.soldOut == true ? laughTrack.colors.textSecondary : laughTrack.colors.accentStrong)
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
        .accessibilityLabel("\(show.name ?? "Untitled show"), \(show.clubName ?? "Unknown club"), \(metadata.joined(separator: ", "))")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(show.imageUrl) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    Rectangle()
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    fallbackArtwork
                @unknown default:
                    fallbackArtwork
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 172)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        } else {
            fallbackArtwork
                .frame(maxWidth: .infinity)
                .frame(height: 172)
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
            ShowFormatting.listDate(show.date),
            show.room,
            ShowFormatting.distance(show.distanceMiles),
        ].compactMap { value in
            guard let value, !value.isEmpty else { return nil }
            return value
        }
    }

    private var lineupPreview: String {
        guard let lineup = show.lineup, !lineup.isEmpty else {
            return "Lineup TBA"
        }

        let names = lineup.prefix(2).map(\.name)
        if lineup.count > 2 {
            return "\(names.joined(separator: ", ")) +\(lineup.count - 2)"
        }
        return names.joined(separator: ", ")
    }
}

private struct HomeShowsTonightRailCard: View {
    let show: Components.Schemas.Show

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            artwork

            Text(show.name ?? "Untitled show")
                .font(laughTrack.typography.cardTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .frame(width: 104, alignment: .leading)

            Text(show.clubName ?? "Unknown club")
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .lineLimit(1)
                .frame(width: 104, alignment: .leading)

            Text(ShowFormatting.listDate(show.date))
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.accentStrong)
                .lineLimit(1)
                .frame(width: 104, alignment: .leading)
        }
        .frame(width: 112, alignment: .topLeading)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(show.name ?? "Untitled show"), \(show.clubName ?? "Unknown club"), \(ShowFormatting.listDate(show.date))")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(show.imageUrl) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    fallbackArtwork
                @unknown default:
                    fallbackArtwork
                }
            }
            .frame(width: 104, height: 78)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "ticket.fill")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .frame(width: 104, height: 78)
    }
}

@MainActor
final class HomeShowsTonightModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle
    @Published private(set) var cityTitle: String?

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?) -> String {
        zipCode ?? ""
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache
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
            badParamsMessage: "LaughTrack could not load tonight's shows.",
            rateLimitMessage: "LaughTrack is rate-limiting tonight's shows right now.",
            undocumentedContext: "tonight's shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the home feed. Check your connection and try again."
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
        cityTitle = Self.locationTitle(city: feed.hero.city, state: feed.hero.state)
        phase = .success(Self.shows(from: feed))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private static func shows(from feed: Components.Schemas.HomeFeed) -> [Components.Schemas.Show] {
        var seenIDs: Set<Int> = []
        return (feed.showsTonight + feed.hero.shows + feed.trendingThisWeek).filter { show in
            seenIDs.insert(show.id).inserted
        }
    }

    private static func locationTitle(city: String?, state: String?) -> String? {
        guard let city, !city.isEmpty else { return nil }
        if let state, !state.isEmpty {
            return "\(city), \(state)"
        }
        return city
    }
}

private struct HomeFavoriteShowsRail: View {
    let apiClient: Client
    let cache: DataCache<LaughTrackCacheKey>

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @StateObject private var model = HomeFavoriteShowsModel()

    private var favoriteComedians: [Components.Schemas.ComedianSearchItem] {
        guard authManager.currentSession != nil,
              favorites.savedFavoritesPhase == .loaded
        else { return [] }

        return favorites.savedFavoriteComedians
    }

    private var requestKey: String {
        favoriteComedians.map(\.uuid).joined(separator: "|")
    }

    var body: some View {
        Group {
            switch model.phase {
            case .success(let shows) where !shows.isEmpty:
                favoriteShowsContent(shows)
            default:
                EmptyView()
            }
        }
        .task(id: requestKey) {
            await model.refresh(apiClient: apiClient, favoriteComedians: favoriteComedians, cache: cache)
        }
    }

    private func favoriteShowsContent(_ shows: [Components.Schemas.Show]) -> some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Favorites",
                title: "Your favorites are touring",
                subtitle: "Upcoming shows featuring comedians you saved."
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
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
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
            from: cache
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
        await MainPageCache.set(shows, forKey: .favoriteShows(requestKey: requestKey), in: cache, ttl: cacheTTL)
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
                eyebrow: "Trending comedians",
                title: "Comics drawing crowds",
                subtitle: "Photo-backed performers with upcoming shows."
            )

            switch model.phase {
            case .idle, .loading:
                LoadingCard(title: "Loading comedians")
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.refresh(apiClient: apiClient, zipCode: zipCode, cache: cache) },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let items):
                if items.isEmpty {
                    EmptyCard(message: "No trending comedians with photos are available right now.")
                } else {
                    ScrollView(.horizontal, showsIndicators: false) {
                        LazyHStack(alignment: .top, spacing: theme.spacing.sm) {
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
                        .padding(.horizontal, 1)
                        .padding(.vertical, 2)
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingComediansRail)
                }
            }
        }
        .task(id: model.requestKey(for: zipCode)) {
            await model.refresh(apiClient: apiClient, zipCode: zipCode, cache: cache)
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
}

private struct HomeTrendingComedianCard: View {
    let comedian: Components.Schemas.ComedianListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            artwork

            Text(comedian.name)
                .font(laughTrack.typography.cardTitle)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(width: 104, alignment: .leading)

            Text(upcomingShowsText)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .lineLimit(1)
                .frame(width: 104, alignment: .leading)
        }
        .frame(width: 112, alignment: .topLeading)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(comedian.name), \(upcomingShowsText)")
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            Image(systemName: "photo")
                                .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        }
                @unknown default:
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(laughTrack.colors.surfaceMuted)
                }
            }
            .frame(width: 104, height: 104)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        } else {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(laughTrack.colors.surfaceMuted)
                .overlay {
                    Image(systemName: "music.mic")
                        .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.accentStrong)
                }
                .frame(width: 104, height: 104)
        }
    }

    private var upcomingShowsText: String {
        "\(comedian.showCount) upcoming show\(comedian.showCount == 1 ? "" : "s")"
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
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode),
            from: cache
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
            networkMessage: "LaughTrack couldn't reach the trending comedians service. Check your connection and try again."
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

enum MainPageCache {
    static let defaultTTL: TimeInterval = 60 * 60

    static func get<Value>(
        _ key: LaughTrackCacheKey,
        from cache: DataCache<LaughTrackCacheKey>?
    ) async -> Value? {
        guard let cache else { return nil }
        return await cache.get(forKey: key)
    }

    static func set(
        _ value: some Sendable,
        forKey key: LaughTrackCacheKey,
        in cache: DataCache<LaughTrackCacheKey>?,
        ttl: TimeInterval = defaultTTL
    ) async {
        guard let cache else { return }
        await cache.set(value, forKey: key, ttl: ttl)
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
        networkMessage: String
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
                    ttl: cacheTTL
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
