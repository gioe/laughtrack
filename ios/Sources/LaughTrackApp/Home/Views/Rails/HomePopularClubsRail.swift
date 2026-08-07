import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomePopularClubsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomePopularClubsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .posterGrid,
            eyebrow: "Hot Rooms",
            title: "Popular local clubs",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homePopularClubsRail,
            actionTitle: "See all",
            action: {
                searchNavigationBridge.openSearch(
                    .discoverEntity(
                        .clubs,
                        nearbyPreference: nearbyPreferenceStore.preference ?? nearbyPreferenceStore.defaultPreference
                    )
                )
            }
        ) {
            switch model.phase {
            case .idle, .loading:
                HomePopularClubsGridSkeleton(gridColumns: gridColumns)
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

private struct HomePopularClubsGridSkeleton: View {
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

                        Circle()
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
        .accessibilityLabel("Loading popular clubs")
        .accessibilityAddTraits(.isImage)
    }
}

struct HomePopularClubCard: View {
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
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(club.name)
    }

    private static let posterSize: CGFloat = 86
    private static let posterFrameInset: CGFloat = 6
    private static let posterCornerRadius: CGFloat = 8
    private static let clubBulbColor = Color(red: 1.0, green: 0.78, blue: 0.24)
    private static let stageHeight: CGFloat = 116

    private var artwork: some View {
        return ZStack {
            HomeMarqueeStageBackground()

            ZStack {
                posterImage
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .clipShape(RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous)
                            .stroke(Color.black.opacity(0.55), lineWidth: 1)
                    )

                HomeBulbFrame(
                    width: Self.posterSize + Self.posterFrameInset,
                    height: Self.posterSize + Self.posterFrameInset,
                    cornerRadius: Self.posterCornerRadius + Self.posterFrameInset / 2,
                    dash: [1.2, 10],
                    bulbColor: Self.clubBulbColor
                )
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFit()
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .background(laughTrack.colors.surfaceMuted)
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
                Image(systemName: ArtworkFallbackKind.club.systemImage)
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}
