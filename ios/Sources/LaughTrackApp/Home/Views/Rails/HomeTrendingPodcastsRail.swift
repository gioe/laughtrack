import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeTrendingPodcastsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingPodcastsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .listeningRoom,
            eyebrow: "Funny listening",
            title: "Popular comedy podcasts",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homeTrendingPodcastsRail
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
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
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
