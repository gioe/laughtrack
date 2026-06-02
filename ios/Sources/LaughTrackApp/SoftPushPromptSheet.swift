import SwiftUI
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct SoftPushPromptSheet: View {
    @ObservedObject var coordinator: SoftPushPromptCoordinator

    @Environment(\.appTheme) private var theme
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .topTrailing) {
            laughTrack.colors.canvas
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    ZStack {
                        Circle()
                            .fill(laughTrack.colors.accentStrong.opacity(0.14))
                            .frame(width: 64, height: 64)

                        Image(systemName: "bell.badge.fill")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    }

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text("Get a heads-up when your favorites announce shows")
                            .font(.system(size: 28, weight: .heavy, design: .rounded))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text("Turn on push notifications and LaughTrack will ping you when a comedian you follow books a date near you.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                VStack(spacing: theme.spacing.sm) {
                    LaughTrackButton(
                        "Enable notifications",
                        systemImage: "bell.fill"
                    ) {
                        Task {
                            await coordinator.enableTapped()
                            dismiss()
                        }
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.softPushPromptEnableButton)

                    LaughTrackButton(
                        "Maybe later",
                        systemImage: "clock",
                        tone: .secondary
                    ) {
                        coordinator.deferTapped()
                        dismiss()
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.softPushPromptDeferButton)
                }

                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, theme.spacing.xl * 1.5)
            .padding(.bottom, theme.spacing.xl)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.softPushPromptSheet)
        .presentationDetents([.medium])
        .presentationDragIndicator(.visible)
    }
}
