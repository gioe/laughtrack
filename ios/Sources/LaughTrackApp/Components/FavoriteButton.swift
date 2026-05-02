import SwiftUI
import LaughTrackBridge

struct FavoriteButton: View {
    @Environment(\.appTheme) private var theme

    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            Task {
                await action()
            }
        } label: {
            ZStack {
                Circle()
                    .fill(isFavorite ? laughTrack.colors.highlight : laughTrack.colors.surfaceElevated)
                    .overlay(
                        Circle()
                            .stroke(
                                isFavorite ? laughTrack.colors.accentStrong.opacity(0.35) : laughTrack.colors.borderSubtle,
                                lineWidth: 1
                            )
                    )

                if isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(laughTrack.colors.accent)
                } else {
                    Image(systemName: isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textSecondary)
                }
            }
            .frame(width: 54, height: 54)
            .shadowStyle(laughTrack.shadows.card)
        }
        .buttonStyle(FavoriteIconButtonStyle(animation: laughTrack.motion.tapFeedback))
        .disabled(isPending)
        .accessibilityLabel(isFavorite ? "Remove favorite" : "Add favorite")
    }
}

private struct FavoriteIconButtonStyle: ButtonStyle {
    let animation: Animation

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.94 : 1)
            .opacity(configuration.isPressed ? 0.86 : 1)
            .animation(animation, value: configuration.isPressed)
    }
}
