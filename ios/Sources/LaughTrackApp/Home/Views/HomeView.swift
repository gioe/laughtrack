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
                HomeHeroHeader(
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self)
                )

                SessionBannerCard(signedOutMessage: signedOutMessage)

                VStack(alignment: .leading, spacing: theme.spacing.md) {
                    LaughTrackHeroModule(
                        eyebrow: "Search",
                        title: "Jump back into Search",
                        subtitle: "Move between Shows, Clubs, and Comedians without leaving the same working surface.",
                        ctaTitle: "Shows, clubs, and comics"
                    )

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackBrowseChip("Near Me ready", systemImage: "location.fill", tone: .selected)
                            LaughTrackBrowseChip("Upcoming dates first", systemImage: "sparkles", tone: .accent)
                            LaughTrackBrowseChip("Favorites in profile", systemImage: "star.fill")
                        }
                        .padding(.horizontal, 1)
                    }
                }

                HomeSearchEntryRail(searchNavigationBridge: searchNavigationBridge)

                HomeFavoriteShowsRail(apiClient: apiClient)

                HomeTrendingComediansRail(
                    apiClient: apiClient,
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self)
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

struct HomeHeroHeader: View {
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    var body: some View {
        LaughTrackSectionHeader(
            eyebrow: "Home",
            title: title,
            subtitle: "Browse local momentum, featured shows, and venue spotlights before dropping into Search."
        )
    }

    var title: String {
        guard let city = nearbyPreferenceStore.preference?.city, !city.isEmpty else {
            return "Comedy worth noticing nearby"
        }
        if let state = nearbyPreferenceStore.preference?.state, !state.isEmpty {
            return "What's funny near \(city), \(state)?"
        }
        return "What's funny near \(city)?"
    }
}

private struct HomeFavoriteShowsRail: View {
    let apiClient: Client

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
            await model.refresh(apiClient: apiClient, favoriteComedians: favoriteComedians)
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

    func refresh(
        apiClient: Client,
        favoriteComedians: [Components.Schemas.ComedianSearchItem]
    ) async {
        let requestKey = Self.requestKey(for: favoriteComedians)
        guard !requestKey.isEmpty else {
            loadedRequestKey = nil
            phase = .idle
            return
        }
        if loadedRequestKey == requestKey, case .success = phase {
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

        phase = .success(showsByID.values.sorted { $0.date < $1.date })
        loadedRequestKey = requestKey
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
}

private struct HomeSearchEntryRail: View {
    let searchNavigationBridge: SearchNavigationBridge

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            LaughTrackShelfHeader(
                eyebrow: "Search entry points",
                title: "Open Search from a head start",
                subtitle: "Pick what you’re browsing first, then refine in place."
            )

            VStack(spacing: theme.spacing.sm) {
                HomeSearchEntryCard(config: .shows, searchNavigationBridge: searchNavigationBridge)
                HomeSearchEntryCard(config: .clubs, searchNavigationBridge: searchNavigationBridge)
                HomeSearchEntryCard(config: .comedians, searchNavigationBridge: searchNavigationBridge)
            }
        }
    }
}

private struct HomeTrendingComediansRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

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
                    retry: { await model.refresh(apiClient: apiClient, zipCode: zipCode) },
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
            await model.refresh(apiClient: apiClient, zipCode: zipCode)
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

    func requestKey(for zipCode: String?) -> String {
        zipCode ?? ""
    }

    func refresh(apiClient: Client, zipCode: String?) async {
        let requestKey = requestKey(for: zipCode)
        if loadedRequestKey == requestKey, case .success = phase {
            return
        }

        phase = .loading

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
                phase = .success(Self.railItems(from: response.data.trendingComedians))
                loadedRequestKey = requestKey
            case .badRequest(let badRequest):
                phase = .failure(
                    .badParams((try? badRequest.body.json.error) ?? "LaughTrack could not load trending comedians.")
                )
            case .tooManyRequests(let tooManyRequests):
                phase = .failure(
                    .rateLimited(retryAfter: nil, message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting trending comedians right now.")
                )
            case .internalServerError(let serverError):
                phase = .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                phase = .failure(classifyUndocumented(status: status, context: "trending comedians"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .failure(
                .network("LaughTrack couldn't reach the trending comedians service. Check your connection and try again.")
            )
        }
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
}
