import SwiftUI
import LaughTrackBridge

struct DetailHeroBadge {
    let title: String
    let systemImage: String?
    let tone: LaughTrackBadgeTone
}

struct DetailHeroAction {
    let title: String
    let systemImage: String
    let url: URL?
}

struct DetailHeroFavoriteState {
    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void
}

enum DetailHeroLayout {
    static let imageAspectRatio: CGFloat = 1.55
    static let maximumMediaHeight: CGFloat = 280
    static let compactMediaHeight: CGFloat = 200
    static let actionDiameter: CGFloat = 40
    static let actionLabelVerticalGap: CGFloat = 2
    static let contentSpacingWithActions: CGFloat = 8
    static let favoriteOverlayDiameter: CGFloat = 44
    static let favoriteOverlayTopPadding: CGFloat = 60
    static let favoriteOverlayTrailingPadding: CGFloat = 16
    static let bottomScrimOpacity = 0.94
    static let heroTextShadowOpacity = 0.78

    static func mediaHeight(forWidth width: CGFloat) -> CGFloat {
        min(width / imageAspectRatio, maximumMediaHeight)
    }
}

struct DetailHero: View {
    @Environment(\.appTheme) private var theme
    @State private var imageLoadFailed = false

    let title: String?
    let imageURL: String
    let badges: [DetailHeroBadge]
    var actions: [DetailHeroAction] = []
    var openURL: ((URL) -> Void)?
    var favoriteState: DetailHeroFavoriteState? = nil
    var fallbackSystemImage: String? = nil

    private var hasOverlayContent: Bool {
        let titleVisible = !(title?.isEmpty ?? true)
        let actionsVisible = openURL != nil && actions.contains { $0.url != nil }
        let badgesVisible = !badges.isEmpty
        return titleVisible || actionsVisible || badgesVisible
    }

    private var resolvedImageURL: URL? {
        URL.normalizedExternalURL(imageURL)
    }

    private var hasUsableImage: Bool {
        resolvedImageURL != nil && !imageLoadFailed
    }

    private var resolvedHeight: CGFloat {
        hasOverlayContent ? DetailHeroLayout.maximumMediaHeight : DetailHeroLayout.compactMediaHeight
    }

    @ViewBuilder
    var body: some View {
        if hasOverlayContent || hasUsableImage || fallbackSystemImage != nil {
            heroContent
        } else {
            EmptyView()
        }
    }

    private var heroContent: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack(alignment: .bottomLeading) {
            if let url = resolvedImageURL, !imageLoadFailed {
                CachedAsyncImage(url: url) { image in
                    image
                        .resizable()
                        .scaledToFill()
                        .frame(maxWidth: .infinity, maxHeight: resolvedHeight, alignment: .top)
                } placeholder: {
                    Rectangle()
                        .fill(laughTrack.colors.surfaceElevated)
                        .frame(maxWidth: .infinity, maxHeight: resolvedHeight)
                } error: { _ in
                    fallbackSurface
                        .onAppear { imageLoadFailed = true }
                }
                .frame(maxWidth: .infinity, maxHeight: resolvedHeight)
                .clipped()
            } else {
                fallbackSurface
            }

            if hasOverlayContent {
                LinearGradient(
                    stops: [
                        .init(color: laughTrack.colors.heroStart.opacity(0.10), location: 0.0),
                        .init(color: laughTrack.colors.heroStart.opacity(0.42), location: 0.46),
                        .init(color: laughTrack.colors.heroStart.opacity(DetailHeroLayout.bottomScrimOpacity), location: 1.0)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )

                VStack(alignment: .leading, spacing: actions.isEmpty ? 12 : DetailHeroLayout.contentSpacingWithActions) {
                    if let title, !title.isEmpty {
                        Text(title)
                            .font(laughTrack.typography.hero)
                            .foregroundStyle(Color.white)
                            .lineLimit(2)
                            .minimumScaleFactor(0.82)
                            .fixedSize(horizontal: false, vertical: true)
                            .shadow(
                                color: .black.opacity(DetailHeroLayout.heroTextShadowOpacity),
                                radius: 6,
                                x: 0,
                                y: 3
                            )
                    }

                    if let openURL {
                        let visibleActions = actions.filter { $0.url != nil }
                        if !visibleActions.isEmpty {
                            HStack(spacing: theme.spacing.md) {
                                ForEach(Array(visibleActions.enumerated()), id: \.offset) { _, action in
                                    if let url = action.url {
                                        Button {
                                            openURL(url)
                                        } label: {
                                            VStack(spacing: DetailHeroLayout.actionLabelVerticalGap) {
                                                Image(systemName: action.systemImage)
                                                    .font(.system(size: theme.iconSizes.sm, weight: .bold))
                                                    .foregroundStyle(laughTrack.colors.textPrimary)
                                                    .frame(width: DetailHeroLayout.actionDiameter, height: DetailHeroLayout.actionDiameter)
                                                    .background(laughTrack.colors.surface.opacity(0.94))
                                                    .clipShape(Circle())
                                                    .overlay(
                                                        Circle()
                                                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                                                    )

                                                Text(action.title)
                                                    .font(laughTrack.typography.metadata)
                                                    .foregroundStyle(Color.white)
                                                    .shadow(
                                                        color: .black.opacity(DetailHeroLayout.heroTextShadowOpacity),
                                                        radius: 3,
                                                        x: 0,
                                                        y: 2
                                                    )
                                            }
                                        }
                                        .buttonStyle(.plain)
                                        .accessibilityLabel(action.title)
                                    }
                                }
                            }
                        }
                    }

                    if !badges.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: theme.spacing.sm) {
                                ForEach(Array(badges.enumerated()), id: \.offset) { _, badge in
                                    LaughTrackBadge(
                                        badge.title,
                                        systemImage: badge.systemImage,
                                        tone: badge.tone
                                    )
                                }
                            }
                        }
                    }
                }
                .padding(laughTrack.spacing.heroPadding)
            }
        }
        .frame(height: resolvedHeight)
        .clipped()
        .overlay(alignment: .topTrailing) {
            if let favoriteState {
                FavoriteHeroOverlayButton(state: favoriteState)
                    .padding(.top, DetailHeroLayout.favoriteOverlayTopPadding)
                    .padding(.trailing, DetailHeroLayout.favoriteOverlayTrailingPadding)
            }
        }
    }

    @ViewBuilder
    private var fallbackSurface: some View {
        let laughTrack = theme.laughTrackTokens

        Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .frame(maxWidth: .infinity, maxHeight: resolvedHeight)
            .overlay {
                if let fallbackSystemImage {
                    Image(systemName: fallbackSystemImage)
                        .font(.system(size: 64, weight: .semibold))
                        .foregroundStyle(laughTrack.colors.accentStrong)
                }
            }
    }
}

private struct FavoriteHeroOverlayButton: View {
    @Environment(\.appTheme) private var theme

    let state: DetailHeroFavoriteState

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            Task { await state.action() }
        } label: {
            ZStack {
                Circle()
                    .fill(laughTrack.colors.surface.opacity(0.94))
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                if state.isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(laughTrack.colors.accent)
                } else {
                    Image(systemName: state.isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(state.isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textPrimary)
                }
            }
            .frame(width: DetailHeroLayout.favoriteOverlayDiameter, height: DetailHeroLayout.favoriteOverlayDiameter)
        }
        .buttonStyle(.plain)
        .disabled(state.isPending)
        .accessibilityLabel(state.isFavorite ? "Remove favorite" : "Add favorite")
    }
}
