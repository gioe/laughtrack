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

struct DetailHeroHost {
    let id: Int
    let name: String
    let imageURL: String?
}

enum DetailHeroLayout {
    static let imageAspectRatio: CGFloat = 1.55
    static let maximumMediaHeight: CGFloat = 280
    static let compactMediaHeight: CGFloat = 200
    static let actionDiameter: CGFloat = 40
    static let actionLabelVerticalGap: CGFloat = 2
    static let contentSpacingWithActions: CGFloat = 8
    static let hostAvatarDiameter: CGFloat = 44
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
    var hosts: [DetailHeroHost] = []
    var openURL: ((URL) -> Void)?
    var openComedian: ((Int) -> Void)? = nil
    var fallbackSystemImage: String? = nil

    private var hasOverlayContent: Bool {
        let titleVisible = !(title?.isEmpty ?? true)
        let actionsVisible = openURL != nil && actions.contains { $0.url != nil }
        let hostsVisible = openComedian != nil && !hosts.isEmpty
        let badgesVisible = !badges.isEmpty
        return titleVisible || actionsVisible || hostsVisible || badgesVisible
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

                    if let openComedian, !hosts.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: theme.spacing.md) {
                                ForEach(hosts, id: \.id) { host in
                                    Button {
                                        openComedian(host.id)
                                    } label: {
                                        VStack(spacing: DetailHeroLayout.actionLabelVerticalGap) {
                                            hostAvatar(for: host)

                                            Text("Host")
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
                                    .accessibilityLabel("\(host.name), host")
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
    }

    @ViewBuilder
    private func hostAvatar(for host: DetailHeroHost) -> some View {
        let diameter = DetailHeroLayout.hostAvatarDiameter
        if let imageURL = host.imageURL, let url = URL.normalizedExternalURL(imageURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                hostAvatarFallback
            } error: { _ in
                hostAvatarFallback
            }
            .frame(width: diameter, height: diameter)
            .clipShape(Circle())
            .overlay(
                Circle()
                    .stroke(theme.laughTrackTokens.colors.borderSubtle, lineWidth: 1)
            )
        } else {
            hostAvatarFallback
        }
    }

    private var hostAvatarFallback: some View {
        let laughTrack = theme.laughTrackTokens
        let diameter = DetailHeroLayout.hostAvatarDiameter
        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .frame(width: diameter, height: diameter)
            .overlay {
                Image(systemName: "person.fill")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
            .overlay(
                Circle()
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
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

