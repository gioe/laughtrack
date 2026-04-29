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
    let subtitle: String?
    let imageURL: String
    let badges: [DetailHeroBadge]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .bottomLeading) {
            RemoteImageView(urlString: imageURL, aspectRatio: 0.8, alignment: .top)
                .frame(maxWidth: .infinity)

            LinearGradient(
                colors: [
                    laughTrack.colors.heroStart.opacity(0),
                    laughTrack.colors.heroStart.opacity(0.88)
                ],
                startPoint: .top,
                endPoint: .bottom
            )

            VStack(alignment: .leading, spacing: 12) {
                if let subtitle {
                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textInverse.opacity(0.78))
                        .textCase(.uppercase)
                }
                Text(title)
                    .font(laughTrack.typography.hero)
                    .foregroundStyle(laughTrack.colors.textInverse)

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
        .padding(.horizontal, -theme.spacing.md)
    }
}
