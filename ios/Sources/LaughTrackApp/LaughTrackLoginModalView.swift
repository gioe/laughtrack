import SwiftUI
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LaughTrackLoginModalView: View {
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .topTrailing) {
            laughTrack.colors.canvas
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Laughtrack")
                        .font(.system(size: 18, weight: .heavy, design: .rounded))
                        .foregroundStyle(laughTrack.colors.accentStrong)
                        .textCase(.uppercase)

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text("Welcome back")
                            .font(.system(size: 42, weight: .heavy, design: .rounded))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text("Sign in to save comedians, sync favorites, and recover your session across devices.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                VStack(spacing: laughTrack.spacing.itemGap) {
                    ForEach(AuthProvider.allCases, id: \.self) { provider in
                        Button {
                            signIn(with: provider)
                        } label: {
                            HStack(spacing: laughTrack.spacing.itemGap) {
                                Image(systemName: provider.symbolName)
                                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                                    .frame(width: 24)

                                Text(provider.title)
                                    .font(laughTrack.typography.action)

                                Spacer(minLength: 0)
                            }
                            .foregroundStyle(provider == .apple ? laughTrack.colors.textInverse : laughTrack.colors.textPrimary)
                            .padding(.horizontal, theme.spacing.lg)
                            .padding(.vertical, theme.spacing.md)
                            .frame(maxWidth: .infinity)
                            .background(buttonBackground(for: provider))
                            .overlay(buttonBorder(for: provider))
                            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                }

                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, theme.spacing.xl * 1.5)
            .padding(.bottom, theme.spacing.xl)

            Button {
                loginModalPresenter.dismiss()
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: theme.iconSizes.sm, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .frame(width: 42, height: 42)
                    .background(laughTrack.colors.surfaceElevated)
                    .clipShape(Circle())
                    .overlay(
                        Circle()
                            .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Close")
            .padding(theme.spacing.lg)
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.hidden)
    }

    @ViewBuilder
    private func buttonBackground(for provider: AuthProvider) -> some View {
        let laughTrack = theme.laughTrackTokens

        switch provider {
        case .apple:
            laughTrack.colors.textPrimary
        case .google:
            laughTrack.colors.surfaceElevated
        }
    }

    @ViewBuilder
    private func buttonBorder(for provider: AuthProvider) -> some View {
        let laughTrack = theme.laughTrackTokens

        RoundedRectangle(cornerRadius: laughTrack.radius.pill, style: .continuous)
            .stroke(provider == .google ? laughTrack.colors.borderStrong.opacity(0.55) : .clear, lineWidth: 1)
    }

    private func signIn(with provider: AuthProvider) {
        loginModalPresenter.dismiss()
        dismiss()

        Task {
            await authManager.signIn(with: provider)
        }
    }
}
