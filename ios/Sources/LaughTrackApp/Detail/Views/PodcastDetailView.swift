import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastDetailResponse: Decodable, Equatable, Sendable {
    let podcast: PodcastDetail
    let episodes: [PodcastDetailEpisode]
    let relatedComedians: [PodcastRelatedComedian]
}

struct PodcastDetail: Decodable, Equatable, Sendable {
    let id: Int
    let title: String
    let authorName: String?
    let websiteUrl: String?
    let feedUrl: String?
    let imageUrl: String?
    let description: String?
    let episodeCount: Int
    let hosts: [PodcastDetailHost]
}

struct PodcastDetailHost: Decodable, Identifiable, Equatable, Sendable {
    let id: Int
    let uuid: String
    let name: String
    let imageUrl: String
}

struct PodcastDetailEpisode: Decodable, Identifiable, Equatable, Sendable {
    let id: Int
    let title: String
    let description: String?
    let releaseDate: String?
    let durationSeconds: Int?
    let episodeUrl: String?
    let audioUrl: String?
    let appearances: [PodcastDetailEpisodeAppearance]
}

struct PodcastDetailEpisodeAppearance: Decodable, Identifiable, Equatable, Sendable {
    let id: Int
    let uuid: String
    let name: String
    let imageUrl: String?
}

extension LineupAvatarItem {
    init(appearance: PodcastDetailEpisodeAppearance) {
        self.init(
            id: appearance.id,
            name: appearance.name,
            imageUrl: appearance.imageUrl
        )
    }
}

struct PodcastRelatedComedian: Decodable, Identifiable, Equatable, Sendable {
    let id: Int
    let uuid: String
    let name: String
    let imageUrl: String?
}

protocol PodcastDetailFetching {
    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure>
}

@MainActor
final class PodcastDetailModel: EntityDetailModel<PodcastDetailResponse> {
    let podcastID: Int
    private let fetcher: any PodcastDetailFetching

    init(
        podcastID: Int,
        fetcher: any PodcastDetailFetching
    ) {
        self.podcastID = podcastID
        self.fetcher = fetcher
    }

    func loadIfNeeded(cache: DataCache<LaughTrackCacheKey>? = nil) async {
        if case .idle = phase,
           let cached: PodcastDetailResponse = await MainPageCache.get(
            .podcast(id: String(podcastID)),
            from: cache,
            persistentCache: nil
           ) {
            phase = .success(cached)
            return
        }

        await super.loadIfNeeded {
            let result = await self.fetcher.podcastDetail(id: self.podcastID)
            if case .success(let response) = result {
                await MainPageCache.set(
                    response,
                    forKey: .podcast(id: String(self.podcastID)),
                    in: cache,
                    persistentCache: nil
                )
            }
            return result
        }
    }

    func reload(cache: DataCache<LaughTrackCacheKey>? = nil) async {
        await super.reload {
            let result = await self.fetcher.podcastDetail(id: self.podcastID)
            if case .success(let response) = result {
                await MainPageCache.set(
                    response,
                    forKey: .podcast(id: String(self.podcastID)),
                    in: cache,
                    persistentCache: nil
                )
            }
            return result
        }
    }
}

struct PodcastDetailView: View {
    let podcastID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var model: PodcastDetailModel
    @State private var feedbackMessage: String?

    init(
        podcastID: Int,
        apiClient: Client,
        fetcher: (any PodcastDetailFetching)? = nil
    ) {
        self.podcastID = podcastID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: PodcastDetailModel(
            podcastID: podcastID,
            fetcher: fetcher ?? APIPodcastDetailFetcher(apiClient: apiClient)
        ))
    }

    private var navigationTitle: String {
        if case .success(let response) = model.phase {
            return response.podcast.title
        }
        return ""
    }

    private var podcastFavoriteState: DetailFavoriteState? {
        guard case .success(let response) = model.phase else { return nil }
        let podcast = response.podcast
        let isFavorite = podcastFavorites.value(for: podcast.id)
        return DetailFavoriteState(
            isFavorite: isFavorite,
            isPending: podcastFavorites.isPending(podcast.id),
            action: {
                await toggleFavorite(
                    podcastID: podcast.id,
                    title: podcast.title,
                    currentValue: isFavorite
                )
            }
        )
    }

    private var detailCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                ShowDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload(cache: detailCache) },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let response):
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        MarqueeHero(
                            title: response.podcast.title,
                            imageURL: response.podcast.imageUrl ?? "",
                            thumbnailStyle: .podcastRail,
                            badges: PodcastDetailPresentation.heroBadges(for: response.podcast),
                            actions: PodcastDetailPresentation.heroActions(for: response.podcast),
                            hosts: PodcastDetailPresentation.heroHosts(for: response.podcast),
                            openURL: { url in openURL(url) },
                            openComedian: { coordinator.open(.comedian($0)) },
                            fallbackSystemImage: "headphones"
                        )

                        VStack(alignment: .leading, spacing: 20) {
                            PodcastEpisodeListSection(
                                podcast: response.podcast,
                                episodes: response.episodes,
                                podcastPlayer: podcastPlayer
                            )

                            PodcastRelatedComediansSection(
                                comedians: PodcastDetailPresentation.frequentGuests(for: response),
                                openComedian: { coordinator.open(.comedian($0)) }
                            )
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, theme.spacing.lg)
                    }
                }
                .modifier(DetailAtmosphereScrollContent())
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier("laughtrack.podcast-detail-screen")
        .modifier(DetailAtmosphereRouteBackground())
        .overlay(alignment: .top) {
            DetailChromeBar(
                onBack: { coordinator.pop() },
                onHome: coordinator.detailHomeAction,
                favoriteState: podcastFavoriteState
            )
        }
        .modifier(EntityDetailNavigationChrome(
            entity: .podcast,
            title: navigationTitle,
            favoriteState: podcastFavoriteState
        ))
        .task {
            await model.loadIfNeeded(cache: detailCache)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func toggleFavorite(podcastID: Int, title: String, currentValue: Bool) async {
        let result = await podcastFavorites.toggle(
            podcastID: podcastID,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )

        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: title, isFavorite: next)
        case .signInRequired:
            loginModalPresenter.present()
        case .failure(let message):
            feedbackMessage = message
        }
    }
}

enum PodcastDetailPresentation {
    static func heroBadges(for podcast: PodcastDetail) -> [DetailHeroBadge] {
        []
    }

    /// "Frequent guests" — comedians who appear in 2+ episodes of the podcast,
    /// excluding the podcast's hosts. Capped at 3 and shuffled per render so
    /// the user sees a rotating sample rather than the same alphabetical slice.
    static func frequentGuests(
        for response: PodcastDetailResponse,
        cap: Int = 3
    ) -> [PodcastRelatedComedian] {
        frequentGuests(
            for: response,
            cap: cap,
            randomizer: { $0.shuffled() }
        )
    }

    static func frequentGuests(
        for response: PodcastDetailResponse,
        cap: Int,
        randomizer: ([PodcastRelatedComedian]) -> [PodcastRelatedComedian]
    ) -> [PodcastRelatedComedian] {
        let hostIDs = Set(response.podcast.hosts.map(\.id))
        let hostUUIDs = Set(response.podcast.hosts.map(\.uuid))

        var episodesByComedian: [Int: Set<Int>] = [:]
        var firstAppearance: [Int: PodcastDetailEpisodeAppearance] = [:]

        for episode in response.episodes {
            for appearance in episode.appearances {
                guard !hostIDs.contains(appearance.id), !hostUUIDs.contains(appearance.uuid) else {
                    continue
                }
                episodesByComedian[appearance.id, default: []].insert(episode.id)
                if firstAppearance[appearance.id] == nil {
                    firstAppearance[appearance.id] = appearance
                }
            }
        }

        let eligible = episodesByComedian
            .filter { $0.value.count >= 2 }
            .compactMap { firstAppearance[$0.key] }
            .map { appearance in
                PodcastRelatedComedian(
                    id: appearance.id,
                    uuid: appearance.uuid,
                    name: appearance.name,
                    imageUrl: appearance.imageUrl
                )
            }

        return Array(randomizer(eligible).prefix(cap))
    }

    static func heroHosts(for podcast: PodcastDetail) -> [DetailHeroHost] {
        podcast.hosts.map { host in
            DetailHeroHost(
                id: host.id,
                name: host.name,
                imageURL: host.imageUrl
            )
        }
    }

    static func heroActions(for podcast: PodcastDetail) -> [DetailHeroAction] {
        [
            DetailHeroAction(
                title: "Website",
                systemImage: "arrow.up.right",
                url: URL.normalizedExternalURL(podcast.websiteUrl)
            ),
            DetailHeroAction(
                title: "RSS",
                systemImage: "dot.radiowaves.left.and.right",
                url: URL.normalizedExternalURL(podcast.feedUrl)
            )
        ]
    }

    static func episodeLineup(
        for episode: PodcastDetailEpisode,
        podcast: PodcastDetail
    ) -> [LineupAvatarItem] {
        let hostIDs = Set(podcast.hosts.map(\.id))
        let hostUUIDs = Set(podcast.hosts.map(\.uuid))

        return episode.appearances
            .filter { appearance in
                !hostIDs.contains(appearance.id) && !hostUUIDs.contains(appearance.uuid)
            }
            .map(LineupAvatarItem.init(appearance:))
    }

    static func playbackItem(
        podcast: PodcastDetail,
        episode: PodcastDetailEpisode
    ) -> PodcastPlaybackItem? {
        let audioURL = URL.normalizedExternalURL(episode.audioUrl)
        let episodeURL = URL.normalizedExternalURL(episode.episodeUrl)
        guard audioURL != nil || episodeURL != nil else { return nil }

        return PodcastPlaybackItem(
            id: episode.id,
            podcastID: podcast.id,
            episodeTitle: episode.title,
            podcastName: podcast.title,
            podcastImageURL: podcast.imageUrl,
            displayRole: "",
            audioURL: audioURL,
            episodeURL: episodeURL,
            failedAudioURL: nil
        )
    }

    static func episodeMetadata(for episode: PodcastDetailEpisode) -> String {
        [
            formattedReleaseDate(episode.releaseDate),
            formattedDuration(episode.durationSeconds)
        ]
        .compactMap { $0 }
        .joined(separator: " • ")
        .nonEmpty ?? "Episode"
    }

    private static func formattedReleaseDate(_ value: String?) -> String? {
        guard let value, let date = Date.laughTrackISO8601(value) else { return nil }

        return releaseDateFormatter.string(from: date)
    }

    private static func formattedDuration(_ durationSeconds: Int?) -> String? {
        guard let durationSeconds, durationSeconds >= 60 else { return nil }
        let totalMinutes = durationSeconds / 60
        let hours = totalMinutes / 60
        let minutes = totalMinutes % 60

        if hours > 0, minutes > 0 {
            return "\(hours) hr \(minutes) min"
        }
        if hours > 0 {
            return "\(hours) hr"
        }
        return "\(minutes) min"
    }

    private static let releaseDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "MMM d, yyyy"
        return formatter
    }()
}

private struct PodcastEpisodeListSection: View {
    static let pageSize = 10

    let podcast: PodcastDetail
    let episodes: [PodcastDetailEpisode]
    @ObservedObject var podcastPlayer: PodcastPlaybackController

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var currentPage = 0

    var body: some View {
        let playableEntries: [(item: PodcastPlaybackItem, metadata: String, lineup: [LineupAvatarItem])] = episodes.compactMap { episode in
            guard let item = PodcastDetailPresentation.playbackItem(podcast: podcast, episode: episode) else {
                return nil
            }
            return (
                item,
                PodcastDetailPresentation.episodeMetadata(for: episode),
                PodcastDetailPresentation.episodeLineup(for: episode, podcast: podcast)
            )
        }

        let pageCount = max(1, (playableEntries.count + Self.pageSize - 1) / Self.pageSize)
        let safePage = min(currentPage, pageCount - 1)
        let startIndex = safePage * Self.pageSize
        let endIndex = min(startIndex + Self.pageSize, playableEntries.count)
        let visibleEntries = playableEntries.isEmpty ? [] : Array(playableEntries[startIndex..<endIndex])

        VStack(alignment: .leading, spacing: 12) {
            LaughTrackSectionHeader(eyebrow: "Catalog", title: "Episodes")

            if episodes.isEmpty {
                EmptyCard(
                    title: "No Episodes Found",
                    message: "\(podcast.title) has no episodes on LaughTrack yet."
                )
            } else if playableEntries.isEmpty {
                EmptyCard(
                    title: "No playable episodes yet",
                    message: "LaughTrack has not matched this podcast with playable episodes yet."
                )
            } else {
                ForEach(visibleEntries, id: \.item.id) { entry in
                    PodcastAppearanceRow(
                        item: entry.item,
                        isCurrent: podcastPlayer.currentItem?.id == entry.item.id,
                        lineup: entry.lineup,
                        subtitleOverride: entry.metadata
                    ) {
                        podcastPlayer.start(entry.item)
                    } onOpenComedian: { comedianID in
                        coordinator.open(.comedian(comedianID))
                    }
                }

                if pageCount > 1 {
                    pager(currentPage: safePage, pageCount: pageCount, totalCount: playableEntries.count)
                }
            }
        }
        .onChange(of: episodes.count) { _ in
            currentPage = 0
        }
    }

    @ViewBuilder
    private func pager(currentPage: Int, pageCount: Int, totalCount: Int) -> some View {
        let laughTrack = theme.laughTrackTokens
        let canGoBack = currentPage > 0
        let canGoForward = currentPage < pageCount - 1

        HStack(spacing: theme.spacing.md) {
            Button {
                withAnimation(.easeInOut(duration: 0.18)) {
                    self.currentPage = max(0, currentPage - 1)
                }
            } label: {
                Label("Previous", systemImage: "chevron.left")
                    .labelStyle(.titleAndIcon)
                    .font(laughTrack.typography.metadata.weight(.semibold))
                    .foregroundStyle(canGoBack ? laughTrack.colors.accent : laughTrack.colors.textSecondary.opacity(0.5))
            }
            .buttonStyle(.plain)
            .disabled(!canGoBack)
            .accessibilityLabel("Previous page")

            Spacer(minLength: 0)

            Text("Page \(currentPage + 1) of \(pageCount)")
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .accessibilityLabel("Page \(currentPage + 1) of \(pageCount), \(totalCount) episodes total")

            Spacer(minLength: 0)

            Button {
                withAnimation(.easeInOut(duration: 0.18)) {
                    self.currentPage = min(pageCount - 1, currentPage + 1)
                }
            } label: {
                HStack(spacing: 4) {
                    Text("Next")
                    Image(systemName: "chevron.right")
                }
                .font(laughTrack.typography.metadata.weight(.semibold))
                .foregroundStyle(canGoForward ? laughTrack.colors.accent : laughTrack.colors.textSecondary.opacity(0.5))
            }
            .buttonStyle(.plain)
            .disabled(!canGoForward)
            .accessibilityLabel("Next page")
        }
        .padding(.top, theme.spacing.xs)
    }
}

private struct PodcastRelatedComediansSection: View {
    let comedians: [PodcastRelatedComedian]
    let openComedian: (Int) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        if !comedians.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: "Regulars", title: "Frequent guests")

                LazyVStack(alignment: .leading, spacing: theme.spacing.sm) {
                    ForEach(comedians) { comedian in
                        Button {
                            openComedian(comedian.id)
                        } label: {
                            PodcastRelatedComedianRow(comedian: comedian)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

private struct PodcastRelatedComedianRow: View {
    let comedian: PodcastRelatedComedian

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
            if let imageURL = comedian.imageUrl, let url = URL.normalizedExternalURL(imageURL) {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                } placeholder: {
                    comedianFallback
                } error: { _ in
                    comedianFallback
                }
                .frame(width: 44, height: 44)
                .clipShape(Circle())
            } else {
                comedianFallback
            }

            Text(comedian.name)
                .font(tokens.typography.body.weight(.semibold))
                .foregroundStyle(tokens.colors.textPrimary)
                .lineLimit(1)

            Spacer(minLength: 0)

            Image(systemName: "chevron.right")
                .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                .foregroundStyle(tokens.colors.textSecondary)
        }
        .padding(.horizontal, tokens.browseDensity.compactCardPadding)
        .padding(.vertical, tokens.browseDensity.compactCardPadding)
        .background(tokens.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: tokens.radius.card, style: .continuous)
                .stroke(tokens.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: tokens.radius.card, style: .continuous))
    }

    private var comedianFallback: some View {
        Circle()
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
            .frame(width: 44, height: 44)
            .overlay {
                Image(systemName: "person.fill")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }
}

/// Routes podcast-detail loads through the generated OpenAPI client (and thus
/// TokenRefreshMiddleware), replacing the former hand-rolled URLSession fetcher
/// that skipped auto-refresh on 401 (TASK-3631). The generated
/// `Components.Schemas.PodcastDetailResponse` is mapped to the local
/// `PodcastDetailResponse` the views and cache already consume (see
/// `PodcastDetailResponse.init(schema:)`).
@MainActor
final class APIPodcastDetailFetcher: PodcastDetailFetching {
    private let apiClient: Client

    init(apiClient: Client) {
        self.apiClient = apiClient
    }

    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> {
        do {
            let output = try await apiClient.getPodcast(.init(path: .init(id: id)))
            switch output {
            case .ok(let ok):
                return .success(PodcastDetailResponse(schema: try ok.body.json))
            case .badRequest:
                return .failure(.badParams("LaughTrack could not load this podcast right now."))
            case .notFound:
                return .failure(.unexpected(status: 404, message: "This podcast could not be found."))
            case .tooManyRequests(let tooManyRequests):
                return .failure(.rateLimited(
                    retryAfter: nil,
                    message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting podcast details right now."
                ))
            case .internalServerError(let serverError):
                return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "podcast details"))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "podcast details"))
        }
    }
}

// Maps the generated podcast-detail schema onto the local view/cache model.
extension PodcastDetailResponse {
    init(schema: Components.Schemas.PodcastDetailResponse) {
        self.init(
            podcast: PodcastDetail(schema: schema.podcast),
            episodes: schema.episodes.map(PodcastDetailEpisode.init(schema:)),
            relatedComedians: schema.relatedComedians.map(PodcastRelatedComedian.init(schema:))
        )
    }
}

extension PodcastDetail {
    init(schema: Components.Schemas.PodcastDetailPodcast) {
        self.init(
            id: schema.id,
            title: schema.title,
            authorName: schema.authorName,
            websiteUrl: schema.websiteUrl,
            feedUrl: schema.feedUrl,
            imageUrl: schema.imageUrl,
            description: schema.description,
            episodeCount: schema.episodeCount,
            hosts: schema.hosts.map(PodcastDetailHost.init(schema:))
        )
    }
}

extension PodcastDetailHost {
    init(schema: Components.Schemas.PodcastDetailHost) {
        self.init(id: schema.id, uuid: schema.uuid, name: schema.name, imageUrl: schema.imageUrl)
    }
}

extension PodcastDetailEpisode {
    init(schema: Components.Schemas.PodcastDetailEpisode) {
        self.init(
            id: schema.id,
            title: schema.title,
            description: schema.description,
            releaseDate: schema.releaseDate,
            durationSeconds: schema.durationSeconds,
            episodeUrl: schema.episodeUrl,
            audioUrl: schema.audioUrl,
            appearances: schema.appearances.map(PodcastDetailEpisodeAppearance.init(schema:))
        )
    }
}

extension PodcastDetailEpisodeAppearance {
    init(schema: Components.Schemas.PodcastDetailEpisodeAppearance) {
        self.init(id: schema.id, uuid: schema.uuid, name: schema.name, imageUrl: schema.imageUrl)
    }
}

extension PodcastRelatedComedian {
    init(schema: Components.Schemas.ComedianSearchItem) {
        self.init(id: schema.id, uuid: schema.uuid, name: schema.name, imageUrl: schema.imageUrl)
    }
}
