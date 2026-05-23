import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct LineupAvatarItem: Identifiable, Equatable {
    let id: Int
    let name: String
    let imageUrl: String?
}

struct LineupAvatarStrip: View {
    let comedians: [LineupAvatarItem]
    var isDimmed = false
    let openComedian: (Int) -> Void

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .top, spacing: theme.spacing.sm) {
            ForEach(comedians) { comedian in
                Button {
                    openComedian(comedian.id)
                } label: {
                    VStack(spacing: 4) {
                        lineupAvatar(for: comedian)
                        Text(comedian.name)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .lineLimit(1)
                            .minimumScaleFactor(0.85)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open \(comedian.name)")
            }
        }
        .padding(.top, theme.spacing.xxs)
        .saturation(isDimmed ? 0 : 1)
        .opacity(isDimmed ? 0.6 : 1)
    }

    @ViewBuilder
    private func lineupAvatar(for comedian: LineupAvatarItem) -> some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = comedian.imageUrl?.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalized = trimmed?.isEmpty == true ? nil : trimmed

        Group {
            if let url = URL.normalizedExternalURL(normalized) {
                CachedAsyncImage(url: url) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    Circle().fill(laughTrack.colors.surfaceMuted)
                } error: { _ in
                    fallbackAvatar
                }
            } else {
                fallbackAvatar
            }
        }
        .frame(width: 44, height: 44)
        .clipShape(Circle())
    }

    private var fallbackAvatar: some View {
        Circle()
            .fill(theme.laughTrackTokens.colors.surfaceMuted)
            .overlay {
                Image(systemName: "person.fill")
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }
    }
}

extension LineupAvatarItem {
    init(comedian: Components.Schemas.ComedianLineup) {
        self.init(
            id: comedian.id,
            name: comedian.name,
            imageUrl: comedian.imageUrl
        )
    }
}
