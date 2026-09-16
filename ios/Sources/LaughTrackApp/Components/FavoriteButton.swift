import SwiftUI
import LaughTrackBridge

/// Search and Library share a quieter accessory treatment without changing
/// standalone favorite controls, such as onboarding.
struct FavoriteButtonPresentation {
    var isCompact = false
    var entityName: String?
    var accessibilityIdentifier: String?
}

private struct FavoriteButtonPresentationKey: EnvironmentKey {
    static let defaultValue = FavoriteButtonPresentation()
}

extension EnvironmentValues {
    var favoriteButtonPresentation: FavoriteButtonPresentation {
        get { self[FavoriteButtonPresentationKey.self] }
        set { self[FavoriteButtonPresentationKey.self] = newValue }
    }
}

struct FavoriteButton: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.favoriteButtonPresentation) private var presentation

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
                if !presentation.isCompact {
                    Circle()
                        .fill(isFavorite ? laughTrack.colors.highlight : laughTrack.colors.surfaceElevated)
                        .overlay(
                            Circle()
                                .stroke(
                                    isFavorite ? laughTrack.colors.accentStrong.opacity(0.35) : laughTrack.colors.borderSubtle,
                                    lineWidth: 1
                                )
                        )
                        .shadowStyle(laughTrack.shadows.card)
                }

                if isPending {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .environment(\.dynamicTypeSize, presentation.isCompact ? .large : dynamicTypeSize)
                        .tint(laughTrack.colors.accent)
                } else {
                    Image(systemName: isFavorite ? "heart.fill" : "heart")
                        .font(.system(size: presentation.isCompact ? 20 : theme.iconSizes.md, weight: .semibold))
                        .foregroundStyle(isFavorite ? laughTrack.colors.accentStrong : laughTrack.colors.textSecondary)
                }
            }
            .frame(width: presentation.isCompact ? 44 : 54, height: presentation.isCompact ? 44 : 54)
            .contentShape(Rectangle())
        }
        .buttonStyle(FavoriteIconButtonStyle(animation: laughTrack.motion.tapFeedback))
        .disabled(isPending)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityValue(isPending ? "Updating" : (isFavorite ? "Saved" : "Not saved"))
        .accessibilityIdentifier(presentation.accessibilityIdentifier ?? "")
    }

    private var accessibilityLabel: String {
        guard let name = presentation.entityName else {
            return isFavorite ? "Remove favorite" : "Add favorite"
        }
        return isFavorite ? "Remove \(name) from favorites" : "Add \(name) to favorites"
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
