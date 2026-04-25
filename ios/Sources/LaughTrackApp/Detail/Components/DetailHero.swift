import SwiftUI
import LaughTrackBridge

struct DetailHeroBadge {
    let title: String
    let systemImage: String?
    let tone: LaughTrackBadgeTone
}

struct DetailHero: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    let imageURL: String
    let badges: [DetailHeroBadge]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(tone: .accent) {
            VStack(alignment: .leading, spacing: 12) {
                RemoteImageView(urlString: imageURL, aspectRatio: 1.7)
                    .frame(maxWidth: .infinity)
                    .frame(height: 220)
                    .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .textCase(.uppercase)
                Text(title)
                    .font(laughTrack.typography.hero)
                    .foregroundStyle(laughTrack.colors.textPrimary)

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
        }
    }
}
