import SwiftUI
import LaughTrackCore

struct SignedOutAuthOption: Identifiable, Equatable, Sendable {
    let provider: AuthProvider
    let title: String
    let symbolName: String

    var id: AuthProvider { provider }

    static let all: [SignedOutAuthOption] = AuthProvider.allCases.map {
        SignedOutAuthOption(
            provider: $0,
            title: $0.title,
            symbolName: $0.symbolName
        )
    }
}

struct SignedOutAuthOptionButton: View {
    @Environment(\.appTheme) private var theme

    let option: SignedOutAuthOption
    let action: (AuthProvider) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            action(option.provider)
        } label: {
            HStack(spacing: theme.spacing.sm) {
                Image(systemName: option.symbolName)
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .frame(width: 24)

                Text(option.title)
                    .font(.system(size: 16, weight: .medium))
                    .lineLimit(1)
                    .minimumScaleFactor(0.86)
            }
            .foregroundStyle(option.provider == .apple ? laughTrack.colors.textInverse : laughTrack.colors.textPrimary)
            .frame(maxWidth: .infinity, minHeight: 44)
            .padding(.horizontal, theme.spacing.md)
            .contentShape(Rectangle())
            .background(buttonBackground)
            .overlay(buttonBorder)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(option.title)
    }

    @ViewBuilder
    private var buttonBackground: some View {
        let laughTrack = theme.laughTrackTokens

        switch option.provider {
        case .apple:
            laughTrack.colors.textPrimary
        case .google, .email:
            laughTrack.colors.surfaceElevated
        }
    }

    private var buttonBorder: some View {
        let laughTrack = theme.laughTrackTokens

        return RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
            .stroke(option.provider == .apple ? .clear : laughTrack.colors.borderStrong.opacity(0.5), lineWidth: 1)
    }
}
