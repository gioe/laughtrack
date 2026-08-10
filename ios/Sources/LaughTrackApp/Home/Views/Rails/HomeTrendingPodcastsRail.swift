import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastEpisodeDiscoveryItem: Identifiable, Equatable {
    let id: Int
    let title: String
    let podcastName: String
    let artworkURL: String?
    let releaseMetadata: String
    let comedianName: String
    let comedianRole: String
    let playbackItem: PodcastPlaybackItem?
}

enum HomePodcastEpisodeDiscoveryPresentation {
    static func item(
        from episode: Components.Schemas.HomeFeedPodcastEpisode,
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> PodcastEpisodeDiscoveryItem {
        let recommendation = episode.recommendation
        let audioURL = URL.normalizedExternalURL(episode.audioUrl)
        let releaseDate = iso8601Formatter.string(from: episode.releaseDate)
        let playbackItem = audioURL.map { audioURL in
            PodcastPlaybackItem(
                id: episode.id,
                episodeID: episode.id,
                podcastID: episode.podcast.id,
                episodeTitle: episode.title,
                podcastName: episode.podcast.title,
                podcastImageURL: episode.podcast.imageUrl,
                displayRole: roleLabel(recommendation.appearanceRole),
                audioURL: audioURL,
                episodeURL: URL.normalizedExternalURL(episode.episodeUrl),
                failedAudioURL: nil,
                releaseDate: releaseDate
            )
        }

        return PodcastEpisodeDiscoveryItem(
            id: episode.id,
            title: episode.title,
            podcastName: episode.podcast.title,
            artworkURL: episode.podcast.imageUrl,
            releaseMetadata: releaseMetadata(
                date: episode.releaseDate,
                durationSeconds: episode.durationSeconds,
                now: now,
                calendar: calendar
            ),
            comedianName: recommendation.comedian.name,
            comedianRole: roleLabel(recommendation.appearanceRole),
            playbackItem: playbackItem
        )
    }

    static func route(for item: PodcastEpisodeDiscoveryItem) -> AppRoute {
        .podcastEpisodeDetail(item.id)
    }

    private static func releaseMetadata(
        date: Date,
        durationSeconds: Int?,
        now: Date,
        calendar: Calendar
    ) -> String {
        let releaseDay = calendar.startOfDay(for: date)
        let today = calendar.startOfDay(for: now)
        let elapsedDays = max(0, calendar.dateComponents([.day], from: releaseDay, to: today).day ?? 0)
        let freshness: String
        switch elapsedDays {
        case 0:
            freshness = "Today"
        case 1:
            freshness = "Yesterday"
        case 2...6:
            freshness = "\(elapsedDays)d ago"
        default:
            freshness = releaseDateFormatter.string(from: date)
        }

        guard let durationSeconds, durationSeconds > 0 else { return freshness }
        let minutes = max(1, Int((Double(durationSeconds) / 60).rounded()))
        return "\(freshness) · \(minutes) min"
    }

    private static func roleLabel(
        _ role: Components.Schemas.HomeFeedPodcastEpisodeRecommendation.AppearanceRolePayload
    ) -> String {
        switch role {
        case .host: return "Host"
        case .cohost: return "Cohost"
        case .guest: return "Guest"
        }
    }

    private static let releaseDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "MMM d"
        return formatter
    }()

    private static let iso8601Formatter = ISO8601DateFormatter()
}

struct HomeTrendingPodcastsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @StateObject private var model = HomeTrendingPodcastsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    private var sessionDiscriminator: String? {
        guard let userId = authManager.currentUser?.userId,
              let session = authManager.currentSession else { return nil }
        return "\(userId)|\(session.signedInAt.timeIntervalSinceReferenceDate)"
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .listeningRoom,
            eyebrow: "Funny listening",
            title: railTitle,
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homeTrendingPodcastsRail,
            actionTitle: displaysBrowsePodcastsAction ? "Browse podcasts" : nil,
            action: {
                searchNavigationBridge.openSearch(.discoverEntity(.podcasts))
            }
        ) {
            switch model.phase {
            case .idle, .loading:
                HomeTrendingPodcastsGridSkeleton(gridColumns: gridColumns)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            sessionDiscriminator: sessionDiscriminator,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let content):
                switch content {
                case .episodes(let episodes):
                    VStack(spacing: theme.spacing.sm) {
                        ForEach(episodes, id: \.id) { episode in
                            let item = HomePodcastEpisodeDiscoveryPresentation.item(from: episode)
                            PodcastEpisodeDiscoveryRow(
                                item: item,
                                onSelect: {
                                    coordinator.push(HomePodcastEpisodeDiscoveryPresentation.route(for: item))
                                },
                                onPlay: item.playbackItem.map { playbackItem in
                                    { podcastPlayer.start(playbackItem) }
                                }
                            )
                        }
                    }
                case .legacyPodcasts(let podcasts):
                    if podcasts.isEmpty {
                        EmptyCard(message: "No comedy podcasts are available right now.")
                    } else {
                        LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                            ForEach(podcasts, id: \.id) { podcast in
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
        }
        .task(id: model.requestKey(
            for: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                sessionDiscriminator: sessionDiscriminator,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private var railTitle: String {
        if case .success(.legacyPodcasts) = model.phase {
            return "Popular comedy podcasts"
        }
        return "Episodes for you"
    }

    private var displaysBrowsePodcastsAction: Bool {
        if case .success(.legacyPodcasts) = model.phase {
            return true
        }
        return false
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

struct PodcastEpisodeDiscoveryRow: View {
    let item: PodcastEpisodeDiscoveryItem
    let onSelect: () -> Void
    let onPlay: (() -> Void)?

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .center, spacing: theme.spacing.sm) {
            Button(action: onSelect) {
                HStack(alignment: .top, spacing: theme.spacing.sm) {
                    artwork

                    VStack(alignment: .leading, spacing: 4) {
                        Text(item.podcastName)
                            .font(laughTrack.typography.metadata.weight(.bold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                            .lineLimit(1)

                        Text(item.title)
                            .font(laughTrack.typography.body.weight(.semibold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .multilineTextAlignment(.leading)
                            .lineLimit(2)

                        Text(item.releaseMetadata)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)

                        Text("\(item.comedianRole): \(item.comedianName)")
                            .font(laughTrack.typography.metadata.weight(.semibold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(1)

                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                [
                    "Open \(item.title)",
                    item.podcastName,
                    item.releaseMetadata,
                    "\(item.comedianRole) \(item.comedianName)",
                ]
                .joined(separator: ", ")
            )
            .accessibilityIdentifier(LaughTrackViewTestID.homePodcastEpisodeButton(item.id))

            if let onPlay {
                Button(action: onPlay) {
                    Image(systemName: "play.circle.fill")
                        .font(.system(size: 28, weight: .semibold))
                        .symbolRenderingMode(.palette)
                        .foregroundStyle(laughTrack.colors.accentStrong, laughTrack.colors.surfaceElevated)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Play \(item.title)")
                .accessibilityIdentifier(LaughTrackViewTestID.homePodcastEpisodePlayButton(item.id))
            }
        }
        .padding(theme.spacing.sm)
        .background(laughTrack.colors.surface)
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    @ViewBuilder
    private var artwork: some View {
        let laughTrack = theme.laughTrackTokens
        let fallback = RoundedRectangle(cornerRadius: 10, style: .continuous)
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.podcast.systemImage)
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }

        Group {
            if let url = URL.normalizedExternalURL(item.artworkURL) {
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
        .frame(width: 78, height: 78)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

private struct HomeTrendingPodcastsGridSkeleton: View {
    @Environment(\.appTheme) private var theme

    let gridColumns: [GridItem]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceSkeleton

        LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
            ForEach(0..<4, id: \.self) { _ in
                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(laughTrack.colors.heroStart)

                        RoundedRectangle(cornerRadius: 7, style: .continuous)
                            .fill(block)
                            .frame(width: 86, height: 86)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 116)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(height: 14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(theme.spacing.sm)
                .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
                .background(laughTrack.colors.surface)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading trending podcasts")
        .accessibilityAddTraits(.isImage)
    }
}

private struct HomeTrendingPodcastCard: View {
    let podcast: Components.Schemas.HomeFeedPodcast

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            Text(podcast.title)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(podcast.title)
    }

    private static let coverSize: CGFloat = 88
    private static let coverCornerRadius: CGFloat = 8
    private static let stageHeight: CGFloat = 116

    private var artwork: some View {
        return ZStack {
            HomeMarqueeStageBackground(glowOpacity: 0.16)

            VStack(spacing: 7) {
                podcastCover
                waveformStrip
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var podcastCover: some View {
        posterImage
            .frame(width: Self.coverSize, height: Self.coverSize)
            .clipShape(RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous)
                    .stroke(Color.black.opacity(0.55), lineWidth: 1)
            )
            .overlay(alignment: .topTrailing) {
                rssBadge
                    .padding(5)
            }
            .shadow(color: .black.opacity(0.42), radius: 8, y: 5)
    }

    private var rssBadge: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            Circle()
                .fill(Color.black.opacity(0.72))

            Image(systemName: "dot.radiowaves.left.and.right")
                .font(.system(size: 11, weight: .heavy))
                .foregroundStyle(laughTrack.colors.accentStrong)
        }
        .frame(width: 24, height: 24)
        .overlay(
            Circle()
                .stroke(laughTrack.colors.accentStrong.opacity(0.92), lineWidth: 1)
        )
        .shadow(color: laughTrack.colors.accentStrong.opacity(0.35), radius: 6)
    }

    private var waveformStrip: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(spacing: 3) {
            Image(systemName: "waveform")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(laughTrack.colors.accentStrong.opacity(0.92))

            HStack(alignment: .center, spacing: 2) {
                ForEach(0..<9, id: \.self) { index in
                    Capsule(style: .continuous)
                        .fill(laughTrack.colors.accentStrong.opacity(0.92))
                        .frame(width: 2, height: CGFloat([7, 13, 9, 18, 11, 15, 8, 12, 6][index]))
                }
            }
        }
        .padding(.horizontal, 8)
        .frame(height: 18)
        .background(Color.black.opacity(0.36), in: Capsule(style: .continuous))
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = podcast.imageUrl?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let raw = trimmed, let url = URL.normalizedExternalURL(raw) {
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
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.podcast.systemImage)
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}
