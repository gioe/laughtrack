import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastDetailResponse: Decodable, Equatable {
    let podcast: PodcastDetail
    let episodes: [PodcastDetailEpisode]
    let relatedComedians: [PodcastRelatedComedian]
}

struct PodcastDetail: Decodable, Equatable {
    let id: Int
    let title: String
    let authorName: String?
    let websiteUrl: String?
    let feedUrl: String?
    let imageUrl: String?
    let description: String?
    let episodeCount: Int
}

struct PodcastDetailEpisode: Decodable, Identifiable, Equatable {
    let id: Int
    let title: String
    let description: String?
    let releaseDate: String?
    let durationSeconds: Int?
    let episodeUrl: String?
    let audioUrl: String?
}

struct PodcastRelatedComedian: Decodable, Identifiable, Equatable {
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
        fetcher: any PodcastDetailFetching = URLSessionPodcastDetailFetcher()
    ) {
        self.podcastID = podcastID
        self.fetcher = fetcher
    }

    func loadIfNeeded() async {
        await super.loadIfNeeded {
            await self.fetcher.podcastDetail(id: self.podcastID)
        }
    }

    func reload() async {
        await super.reload {
            await self.fetcher.podcastDetail(id: self.podcastID)
        }
    }
}

struct PodcastDetailView: View {
    let podcastID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
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
            fetcher: fetcher ?? URLSessionPodcastDetailFetcher()
        ))
    }

    private var navigationTitle: String {
        if case .success(let response) = model.phase {
            return response.podcast.title
        }
        return ""
    }

    var body: some View {
        Group {
            switch model.phase {
            case .idle, .loading:
                ShowDetailSkeleton()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.reload() },
                    signIn: { coordinator.push(.profile) }
                )
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .success(let response):
                let isFavorite = podcastFavorites.value(for: response.podcast.id)
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        DetailHero(
                            title: response.podcast.title,
                            subtitle: PodcastDetailPresentation.subtitle(for: response.podcast),
                            imageURL: response.podcast.imageUrl ?? "",
                            badges: PodcastDetailPresentation.heroBadges(for: response.podcast),
                            actions: PodcastDetailPresentation.heroActions(for: response.podcast),
                            openURL: { url in openURL(url) },
                            favoriteState: DetailHeroFavoriteState(
                                isFavorite: isFavorite,
                                isPending: podcastFavorites.isPending(response.podcast.id),
                                action: {
                                    await toggleFavorite(
                                        podcastID: response.podcast.id,
                                        title: response.podcast.title,
                                        currentValue: isFavorite
                                    )
                                }
                            )
                        )
                        .ignoresSafeArea(.container, edges: .top)

                        VStack(alignment: .leading, spacing: 20) {
                            if let description = response.podcast.description?.nonEmpty {
                                DetailTextCard(eyebrow: "Podcast", title: "About the show", text: description)
                            }

                            PodcastEpisodeListSection(
                                podcast: response.podcast,
                                episodes: response.episodes,
                                podcastPlayer: podcastPlayer
                            )

                            PodcastRelatedComediansSection(
                                comedians: response.relatedComedians,
                                openComedian: { coordinator.open(.comedian($0)) }
                            )
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, theme.spacing.lg)
                    }
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier("laughtrack.podcast-detail-screen")
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .modifier(EntityDetailNavigationChrome(entity: .podcast, title: navigationTitle))
        .task {
            await model.loadIfNeeded()
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
    static func subtitle(for podcast: PodcastDetail) -> String? {
        podcast.authorName.map { "Hosted by \($0)" }
    }

    static func heroBadges(for podcast: PodcastDetail) -> [DetailHeroBadge] {
        [
            DetailHeroBadge(
                title: "\(podcast.episodeCount) episodes",
                systemImage: "headphones",
                tone: .accent
            )
        ]
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
        guard let value, !value.isEmpty else { return nil }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let date = formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
        guard let date else { return nil }

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
    let podcast: PodcastDetail
    let episodes: [PodcastDetailEpisode]
    @ObservedObject var podcastPlayer: PodcastPlaybackController

    @Environment(\.appTheme) private var theme

    var body: some View {
        let playableEntries: [(item: PodcastPlaybackItem, metadata: String)] = episodes.compactMap { episode in
            guard let item = PodcastDetailPresentation.playbackItem(podcast: podcast, episode: episode) else {
                return nil
            }
            return (item, PodcastDetailPresentation.episodeMetadata(for: episode))
        }

        VStack(alignment: .leading, spacing: 12) {
            LaughTrackSectionHeader(title: "Episodes")

            if playableEntries.isEmpty {
                EmptyCard(
                    title: "No playable episodes yet",
                    message: "LaughTrack has not matched this podcast with playable episodes yet."
                )
            } else {
                ForEach(playableEntries, id: \.item.id) { entry in
                    PodcastAppearanceRow(
                        item: entry.item,
                        isCurrent: podcastPlayer.currentItem?.id == entry.item.id,
                        subtitleOverride: entry.metadata
                    ) {
                        podcastPlayer.start(entry.item)
                    }
                }
            }
        }
    }
}

private struct PodcastRelatedComediansSection: View {
    let comedians: [PodcastRelatedComedian]
    let openComedian: (Int) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            LaughTrackSectionHeader(title: "Related comedians")

            if comedians.isEmpty {
                EmptyCard(
                    title: "No related comedians yet",
                    message: "LaughTrack has not matched comedians to this podcast yet."
                )
            } else {
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

private final class URLSessionPodcastDetailFetcher: PodcastDetailFetching {
    private let baseURL: URL
    private let urlSession: URLSession

    init(
        baseURL: URL = AppConfiguration.apiBaseURL,
        urlSession: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.urlSession = urlSession
    }

    func podcastDetail(id: Int) async -> Result<PodcastDetailResponse, LoadFailure> {
        let url = baseURL
            .appendingPathComponent("api")
            .appendingPathComponent("v1")
            .appendingPathComponent("podcasts")
            .appendingPathComponent(String(id))

        do {
            let (data, response) = try await urlSession.data(from: url)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0

            switch status {
            case 200:
                return .success(try JSONDecoder().decode(PodcastDetailResponse.self, from: data))
            case 400:
                return .failure(.badParams("LaughTrack could not load this podcast right now."))
            case 404:
                return .failure(.unexpected(status: 404, message: "This podcast could not be found."))
            case 429:
                return .failure(.rateLimited(retryAfter: nil, message: "LaughTrack is rate-limiting podcast details right now."))
            case 500..<600:
                return .failure(.serverError(status: status, message: nil))
            default:
                return .failure(.unexpected(status: status, message: "LaughTrack returned an unexpected podcast response."))
            }
        } catch is DecodingError {
            return .failure(.decoding("LaughTrack reached the podcast service, but could not read the response. Please try again."))
        } catch {
            return .failure(classifyDetailFetchError(error, context: "podcast details"))
        }
    }
}
