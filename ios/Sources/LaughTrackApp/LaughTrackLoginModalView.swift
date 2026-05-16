import SwiftUI
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LaughTrackLoginModalView: View {
    static let signedOutAuthOptions = SignedOutAuthOption.all

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .topTrailing) {
            laughTrack.colors.canvas
                .ignoresSafeArea()

            VStack(spacing: laughTrack.spacing.sectionGap) {
                VStack(spacing: laughTrack.spacing.itemGap) {
                    Image("LaunchLogo")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 120, height: 120)

                    VStack(spacing: laughTrack.spacing.tight) {
                        Text("Pick up where you left off")
                            .font(laughTrack.typography.screenTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)

                        Text("Sign in to favorite comedians, get alerts when they tour near you, and sync your saves across devices.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                VStack(spacing: laughTrack.spacing.itemGap) {
                    ForEach(Self.signedOutAuthOptions) { option in
                        SignedOutAuthOptionButton(option: option, action: signIn)
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

    private func signIn(with provider: AuthProvider) {
        loginModalPresenter.dismiss()
        dismiss()

        Task {
            await authManager.signIn(with: provider)
        }
    }
}
