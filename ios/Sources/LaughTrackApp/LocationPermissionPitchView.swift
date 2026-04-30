import SwiftUI
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct LocationPermissionPitchView: View {
    @ObservedObject var nearbyLocationController: NearbyLocationController

    let onResolved: () -> Void
    let onManualZip: () -> Void
    let onClose: () -> Void

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

                        Image(systemName: "location.fill")
                            .font(.system(size: 28, weight: .bold))
                            .foregroundStyle(laughTrack.colors.accentStrong)
                    }

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text("Find better comedy nearby")
                            .font(.system(size: 34, weight: .heavy, design: .rounded))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)

                        Text("Let LaughTrack use your location to surface the shows, clubs, and comedians that are actually close enough for tonight.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if let statusMessage = nearbyLocationController.statusMessage {
                    Text(statusMessage)
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.danger)
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(spacing: theme.spacing.sm) {
                    LaughTrackButton(
                        nearbyLocationController.isResolvingCurrentLocation ? "Finding your ZIP..." : "Use my location",
                        systemImage: "location.north.line"
                    ) {
                        Task {
                            let didResolve = await nearbyLocationController.useCurrentLocation(
                                distanceMiles: nearbyLocationController.preference?.distanceMiles
                                    ?? NearbyPreference.defaultDistanceMiles
                            )
                            if didResolve {
                                onResolved()
                                dismiss()
                            }
                        }
                    }
                    .disabled(nearbyLocationController.isResolvingCurrentLocation)
                    .accessibilityIdentifier(LaughTrackViewTestID.locationPermissionAllowButton)

                    LaughTrackButton(
                        "Enter ZIP instead",
                        systemImage: "mappin.and.ellipse",
                        tone: .secondary
                    ) {
                        onManualZip()
                        dismiss()
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.locationPermissionManualZipButton)
                }

                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, theme.spacing.xl * 1.5)
            .padding(.bottom, theme.spacing.xl)

            Button {
                onClose()
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
            .accessibilityIdentifier(LaughTrackViewTestID.locationPermissionCloseButton)
            .padding(theme.spacing.lg)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.locationPermissionPitch)
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }
}
