import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeTrendingComediansRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingComediansModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .posterGrid,
            eyebrow: "Drawing Crowds",
            title: "Popular local comedians",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homeTrendingComediansRail
        ) {
            switch model.phase {
            case .idle, .loading:
                HomeTrendingComediansGridSkeleton(gridColumns: gridColumns)
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

private struct HomeTrendingComediansGridSkeleton: View {
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
        .accessibilityLabel("Loading trending comedians")
        .accessibilityAddTraits(.isImage)
    }
}

private struct HomeTrendingComedianCard: View {
    let comedian: Components.Schemas.ComedianListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        artwork
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(comedian.name)
    }

    private static let stageHeight: CGFloat = 154

    private var artwork: some View {
        GeometryReader { proxy in
            let metrics = headshotMetrics(for: proxy.size.width)

            ClubWallHeadshotFrame(
                caption: comedian.name,
                photoWidth: metrics.photoWidth,
                photoHeight: metrics.photoHeight,
                frameWidth: metrics.frameWidth,
                frameHeight: metrics.frameHeight,
                captionFontSize: metrics.captionFontSize,
                captionWidth: metrics.captionWidth,
                captionHeight: metrics.captionHeight
            ) {
                posterImage
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
    }

    private func headshotMetrics(for availableWidth: CGFloat) -> HomeShowsTonightPortraitMetrics {
        let scale = min(1.0, max(0.82, availableWidth / 156))

        return HomeShowsTonightPortraitMetrics(
            photoWidth: 124 * scale,
            photoHeight: 119 * scale,
            frameWidth: 144 * scale,
            frameHeight: 154 * scale,
            captionFontSize: 9.0 * scale,
            captionWidth: 116 * scale,
            captionHeight: 16 * scale
        )
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
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
                Image(systemName: ArtworkFallbackKind.comedian.systemImage)
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

}
