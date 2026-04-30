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

enum DetailHeroLayout {
    static let imageAspectRatio: CGFloat = 1.55
    static let maximumMediaHeight: CGFloat = 280
    static let actionDiameter: CGFloat = 40
    static let actionLabelVerticalGap: CGFloat = 2
    static let contentSpacingWithActions: CGFloat = 8

    static func mediaHeight(forWidth width: CGFloat) -> CGFloat {
        min(width / imageAspectRatio, maximumMediaHeight)
    }
}

struct DetailHero: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String?
    let imageURL: String
    let badges: [DetailHeroBadge]
    var actions: [DetailHeroAction] = []
    var openURL: ((URL) -> Void)?

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .bottomLeading) {
            RemoteImageView(urlString: imageURL, aspectRatio: DetailHeroLayout.imageAspectRatio, alignment: .top)
                .frame(maxWidth: .infinity, maxHeight: DetailHeroLayout.maximumMediaHeight)
                .clipped()

            LinearGradient(
                colors: [
                    laughTrack.colors.heroStart.opacity(0),
                    laughTrack.colors.heroStart.opacity(0.88)
                ],
                startPoint: .top,
                endPoint: .bottom
            )

            VStack(alignment: .leading, spacing: actions.isEmpty ? 12 : DetailHeroLayout.contentSpacingWithActions) {
                if let subtitle {
                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                        .textCase(.uppercase)
                }
                Text(title)
                    .font(laughTrack.typography.hero)
                    .foregroundStyle(laughTrack.colors.textInverse)

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
                                                .foregroundStyle(laughTrack.colors.textInverse)
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
        .frame(height: DetailHeroLayout.maximumMediaHeight)
        .clipped()
    }
}
