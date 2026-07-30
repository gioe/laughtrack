import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastEpisodeDetailResponse: Equatable, Sendable {
    let podcast: PodcastDetail
    let episode: PodcastDetailEpisode
}

protocol PodcastEpisodeDetailFetching {
    func podcastEpisodeDetail(id: Int) async -> Result<PodcastEpisodeDetailResponse, LoadFailure>
}

@MainActor
final class PodcastEpisodeDetailModel: EntityDetailModel<PodcastEpisodeDetailResponse> {
    let episodeID: Int
    private let fetcher: any PodcastEpisodeDetailFetching

    init(
        episodeID: Int,
        fetcher: any PodcastEpisodeDetailFetching
    ) {
        self.episodeID = episodeID
        self.fetcher = fetcher
    }

    func loadIfNeeded() async {
        await super.loadIfNeeded {
            await self.fetcher.podcastEpisodeDetail(id: self.episodeID)
        }
    }

    func reload() async {
        await super.reload {
            await self.fetcher.podcastEpisodeDetail(id: self.episodeID)
        }
    }
}

struct PodcastEpisodeDetailLineup: Equatable {
    let hosts: [PodcastDetailHost]
    let guests: [PodcastDetailEpisodeAppearance]
}

enum PodcastEpisodeDetailPrimaryAction: Equatable {
    case play(PodcastPlaybackItem)
    case openOriginal(URL)
    case unavailable
}

enum PodcastEpisodeDetailPresentation {
    static func lineup(for response: PodcastEpisodeDetailResponse) -> PodcastEpisodeDetailLineup {
        let hostIDs = Set(response.podcast.hosts.map(\.id))
        let hostUUIDs = Set(response.podcast.hosts.map(\.uuid))
        let guests = response.episode.appearances.filter {
            !hostIDs.contains($0.id) && !hostUUIDs.contains($0.uuid)
        }

        return PodcastEpisodeDetailLineup(
            hosts: response.podcast.hosts,
            guests: guests
        )
    }

    static func primaryAction(
        for response: PodcastEpisodeDetailResponse
    ) -> PodcastEpisodeDetailPrimaryAction {
        if let audioURL = URL.normalizedExternalURL(response.episode.audioUrl) {
            return .play(
                PodcastPlaybackItem(
                    id: response.episode.id,
                    episodeID: response.episode.id,
                    podcastID: response.podcast.id,
                    episodeTitle: response.episode.title,
                    podcastName: response.podcast.title,
                    podcastImageURL: response.podcast.imageUrl,
                    displayRole: "Episode",
                    audioURL: audioURL,
                    episodeURL: URL.normalizedExternalURL(response.episode.episodeUrl),
                    failedAudioURL: nil,
                    releaseDate: response.episode.releaseDate
                )
            )
        }

        if let episodeURL = URL.normalizedExternalURL(response.episode.episodeUrl) {
            return .openOriginal(episodeURL)
        }

        return .unavailable
    }

    static func metadata(for episode: PodcastDetailEpisode) -> String {
        PodcastDetailPresentation.episodeMetadata(for: episode)
    }
}

struct PodcastEpisodeDetailView: View {
    let episodeID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @StateObject private var model: PodcastEpisodeDetailModel

    init(
        episodeID: Int,
        apiClient: Client,
        fetcher: (any PodcastEpisodeDetailFetching)? = nil
    ) {
        self.episodeID = episodeID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: PodcastEpisodeDetailModel(
            episodeID: episodeID,
            fetcher: fetcher ?? APIPodcastEpisodeDetailFetcher(apiClient: apiClient)
        ))
    }

    private var navigationTitle: String {
        guard case .success(let response) = model.phase else { return "" }
        return response.episode.title
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
                successContent(response)
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .accessibilityIdentifier(LaughTrackViewTestID.podcastEpisodeDetailScreen)
        .modifier(DetailAtmosphereRouteBackground())
        .overlay(alignment: .top) {
            DetailChromeBar(
                onBack: { coordinator.pop() },
                onHome: coordinator.detailHomeAction,
                favoriteState: nil
            )
        }
        .modifier(EntityDetailNavigationChrome(entity: .podcast, title: navigationTitle))
        .task {
            await model.loadIfNeeded()
        }
    }

    private func successContent(_ response: PodcastEpisodeDetailResponse) -> some View {
        ScrollView {
            AdaptiveDetailCatalogLayout {
                MarqueeHero(
                    title: response.episode.title,
                    eyebrow: response.podcast.title,
                    imageURL: response.podcast.imageUrl ?? "",
                    thumbnailStyle: .podcastRail,
                    fallbackSystemImage: ArtworkFallbackKind.podcast.systemImage
                )
            } content: {
                VStack(alignment: .leading, spacing: theme.spacing.lg) {
                    episodeContext(response)
                    primaryAction(for: response)

                    if let description = response.episode.description?
                        .trimmingCharacters(in: .whitespacesAndNewlines),
                       !description.isEmpty {
                        DetailTextCard(
                            eyebrow: "Episode notes",
                            title: "About this episode",
                            text: description
                        )
                    }

                    peopleSections(for: response)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, theme.spacing.lg)
            }
        }
        .modifier(DetailAtmosphereScrollContent())
    }

    private func episodeContext(_ response: PodcastEpisodeDetailResponse) -> some View {
        let tokens = theme.laughTrackTokens

        return LaughTrackCard {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                LaughTrackSectionHeader(
                    eyebrow: "Episode",
                    title: PodcastEpisodeDetailPresentation.metadata(for: response.episode)
                )

                Button {
                    coordinator.open(.podcast(response.podcast.id))
                } label: {
                    HStack(spacing: theme.spacing.sm) {
                        Image(systemName: ArtworkFallbackKind.podcast.systemImage)
                            .foregroundStyle(tokens.colors.accentStrong)

                        Text(response.podcast.title)
                            .font(tokens.typography.body.weight(.semibold))
                            .foregroundStyle(tokens.colors.textPrimary)
                            .multilineTextAlignment(.leading)

                        Spacer(minLength: 0)

                        Image(systemName: "chevron.right")
                            .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                            .foregroundStyle(tokens.colors.textSecondary)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open \(response.podcast.title)")
                .accessibilityIdentifier(LaughTrackViewTestID.podcastEpisodeDetailPodcastLink)
            }
        }
    }

    @ViewBuilder
    private func primaryAction(for response: PodcastEpisodeDetailResponse) -> some View {
        switch PodcastEpisodeDetailPresentation.primaryAction(for: response) {
        case .play(let item):
            LaughTrackButton("Play episode", systemImage: "play.fill") {
                podcastPlayer.start(item)
            }
            .accessibilityIdentifier(LaughTrackViewTestID.podcastEpisodeDetailPrimaryAction)
        case .openOriginal(let url):
            LaughTrackButton("Open original episode", systemImage: "arrow.up.right") {
                openURL(url)
            }
            .accessibilityIdentifier(LaughTrackViewTestID.podcastEpisodeDetailPrimaryAction)
        case .unavailable:
            EmptyCard(
                title: "Playback unavailable",
                message: "This episode's details are available, but LaughTrack does not have audio or an original episode link."
            )
            .accessibilityIdentifier(LaughTrackViewTestID.podcastEpisodeDetailPrimaryAction)
        }
    }

    @ViewBuilder
    private func peopleSections(for response: PodcastEpisodeDetailResponse) -> some View {
        let lineup = PodcastEpisodeDetailPresentation.lineup(for: response)

        if !lineup.hosts.isEmpty {
            PodcastEpisodePeopleSection(
                eyebrow: "Featuring",
                title: lineup.hosts.count == 1 ? "Host" : "Hosts",
                people: lineup.hosts.map {
                    PodcastEpisodePerson(
                        id: $0.id,
                        name: $0.name,
                        imageUrl: $0.imageUrl
                    )
                },
                openComedian: { coordinator.open(.comedian($0)) }
            )
        }

        if !lineup.guests.isEmpty {
            PodcastEpisodePeopleSection(
                eyebrow: "Featuring",
                title: lineup.guests.count == 1 ? "Guest" : "Guests",
                people: lineup.guests.map {
                    PodcastEpisodePerson(
                        id: $0.id,
                        name: $0.name,
                        imageUrl: $0.imageUrl
                    )
                },
                openComedian: { coordinator.open(.comedian($0)) }
            )
        }
    }
}

private struct PodcastEpisodePerson: Identifiable {
    let id: Int
    let name: String
    let imageUrl: String?
}

private struct PodcastEpisodePeopleSection: View {
    let eyebrow: String
    let title: String
    let people: [PodcastEpisodePerson]
    let openComedian: (Int) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let tokens = theme.laughTrackTokens

        LaughTrackCard {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title)

                ForEach(people) { person in
                    Button {
                        openComedian(person.id)
                    } label: {
                        HStack(spacing: theme.spacing.md) {
                            avatar(for: person)

                            Text(person.name)
                                .font(tokens.typography.body.weight(.semibold))
                                .foregroundStyle(tokens.colors.textPrimary)
                                .multilineTextAlignment(.leading)

                            Spacer(minLength: 0)

                            Image(systemName: "chevron.right")
                                .font(.system(size: theme.iconSizes.sm, weight: .semibold))
                                .foregroundStyle(tokens.colors.textSecondary)
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Open \(person.name)")
                    .accessibilityIdentifier(
                        LaughTrackViewTestID.podcastEpisodeDetailComedianLink(person.id)
                    )
                }
            }
        }
    }

    @ViewBuilder
    private func avatar(for person: PodcastEpisodePerson) -> some View {
        let tokens = theme.laughTrackTokens
        let fallback = Circle()
            .fill(tokens.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.person.systemImage)
                    .foregroundStyle(tokens.colors.accentStrong)
            }

        Group {
            if let url = URL.normalizedExternalURL(person.imageUrl) {
                CachedAsyncImage(url: url) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    fallback
                } error: { _ in
                    fallback
                }
            } else {
                fallback
            }
        }
        .frame(width: 44, height: 44)
        .clipShape(Circle())
    }
}

@MainActor
final class APIPodcastEpisodeDetailFetcher: PodcastEpisodeDetailFetching {
    private let apiClient: Client

    init(apiClient: Client) {
        self.apiClient = apiClient
    }

    func podcastEpisodeDetail(id: Int) async -> Result<PodcastEpisodeDetailResponse, LoadFailure> {
        do {
            let output = try await apiClient.getPodcastEpisode(.init(path: .init(id: id)))
            let notFoundMessage = "This podcast episode could not be found."

            switch output {
            case .ok(let ok):
                return .success(PodcastEpisodeDetailResponse(schema: try ok.body.json))
            case .badRequest:
                return .failure(classifyUndocumented(status: 400, context: "podcast episode details"))
            case .notFound:
                return .failure(classifyUndocumented(
                    status: 404,
                    context: "podcast episode details",
                    notFoundMessage: notFoundMessage
                ))
            case .tooManyRequests(let response):
                return .failure(.rateLimited(
                    retryAfter: response.headers.retryAfter.map(TimeInterval.init),
                    message: "LaughTrack is rate-limiting podcast episode details right now."
                ))
            case .internalServerError:
                return .failure(classifyUndocumented(status: 500, context: "podcast episode details"))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(
                    status: status,
                    context: "podcast episode details",
                    notFoundMessage: notFoundMessage
                ))
            }
        } catch {
            return .failure(classifyDetailFetchError(error, context: "podcast episode details"))
        }
    }
}

extension PodcastEpisodeDetailResponse {
    init(schema: Components.Schemas.PodcastEpisodeDetailResponse) {
        self.init(
            podcast: PodcastDetail(schema: schema.podcast),
            episode: PodcastDetailEpisode(schema: schema.episode)
        )
    }
}
