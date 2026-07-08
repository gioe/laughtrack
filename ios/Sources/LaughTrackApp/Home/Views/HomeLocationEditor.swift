import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct HomeLocationPrompt: View {
    let displayPreference: NearbyPreference?
    let isExplicitPreference: Bool

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(alignment: .center, spacing: theme.spacing.sm) {
            Image(systemName: displayPreference == nil ? "location.circle" : "location.fill")
                .font(.system(size: theme.iconSizes.md, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
                .frame(width: 34, height: 34)
                .background(laughTrack.colors.accentStrong.opacity(0.12))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(laughTrack.typography.body.weight(.semibold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(1)

                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 0)

            Image(systemName: "chevron.right")
                .font(.system(size: theme.iconSizes.sm, weight: .bold))
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
        .padding(.horizontal, theme.spacing.md)
        .padding(.vertical, theme.spacing.sm)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .contentShape(Rectangle())
    }

    private var title: String {
        guard let displayPreference else {
            return "Set your location"
        }

        if let city = displayPreference.city, let state = displayPreference.state {
            return "Near \(city), \(state)"
        }

        return "ZIP \(displayPreference.zipCode)"
    }

    private var subtitle: String {
        guard let displayPreference else {
            return "Get shows, clubs, and comedians near you."
        }

        if isExplicitPreference {
            let source = displayPreference.source == .manual ? "Saved ZIP" : "Current location"
            return "\(source) - \(displayPreference.distanceMiles) mi"
        }

        return "Default area - \(displayPreference.distanceMiles) mi"
    }
}

struct HomeLocationEditorSheet: View {
    @ObservedObject var model: SettingsNearbyPreferenceModel
    @Binding var isPresented: Bool

    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            sheetHeader
            zipControl
            distanceControl
            messageArea
            actionStack
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, theme.spacing.lg)
        .padding(.top, theme.spacing.lg)
        .padding(.bottom, theme.spacing.xl)
        .background(sheetBackground)
        .presentationDetents([.height(430), .large])
    }

    private var sheetBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.heroStart

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(0.22),
                    laughTrack.colors.accent.opacity(0.0)
                ],
                center: UnitPoint(x: 0.5, y: 0.18),
                startRadius: 20,
                endRadius: 260
            )
        }
    }

    private var sheetHeader: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(alignment: .top, spacing: theme.spacing.md) {
            Image(systemName: "mappin.and.ellipse")
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(laughTrack.colors.accentStrong)
                .frame(width: 44, height: 44)
                .background(laughTrack.colors.surfaceElevated.opacity(0.92))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )

            VStack(alignment: .leading, spacing: 4) {
                Text("Set your location")
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeLocationSheet)

                Text("Choose where Discover looks for shows, clubs, and comedians.")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)

            Button {
                isPresented = false
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: theme.iconSizes.sm, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .frame(width: 36, height: 36)
                    .background(laughTrack.colors.surfaceElevated.opacity(0.92))
                    .clipShape(Circle())
                    .overlay(Circle().stroke(laughTrack.colors.borderSubtle, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Close")
        }
    }

    private var zipControl: some View {
        let laughTrack = theme.laughTrackTokens

        return LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft) {
            Button {
                applyZip()
            } label: {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accent)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Apply ZIP")
        }
        .modifier(SearchFieldInputBehavior())
        #if os(iOS)
        .keyboardType(UIKeyboardType.numberPad)
        #endif
        .onSubmit(applyZip)
        .accessibilityLabel("Discover location ZIP code")
        .accessibilityIdentifier(LaughTrackViewTestID.homeLocationZipField)
    }

    private var distanceControl: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text("Distance")
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)

            LaughTrackChipPicker(
                options: SettingsNearbyPreferenceModel.distanceOptions,
                selection: $model.distanceMiles,
                accessibilityLabel: "Distance",
                accessibilityIdentifier: LaughTrackViewTestID.homeLocationDistancePicker
            ) { "\($0) mi" }
        }
    }

    @ViewBuilder
    private var messageArea: some View {
        let laughTrack = theme.laughTrackTokens

        if let validationMessage = model.validationMessage {
            Text(validationMessage)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.danger)
                .fixedSize(horizontal: false, vertical: true)
        }

        if let statusMessage = model.statusMessage {
            InlineStatusMessage(message: statusMessage)

            if statusMessage == NearbyLocationError.denied.recoveryMessage {
                LaughTrackButton("Open Settings", systemImage: "gearshape", tone: .secondary, density: .compact, fullWidth: false) {
                    openAppSettings()
                }
            }
        }
    }

    private var actionStack: some View {
        VStack(spacing: theme.spacing.sm) {
            LaughTrackButton("Apply ZIP", systemImage: "checkmark", density: .compact) {
                applyZip()
            }
            .accessibilityIdentifier(LaughTrackViewTestID.homeLocationApplyButton)

            LaughTrackButton(
                model.isResolvingCurrentLocation ? "Finding ZIP..." : "Use my location",
                systemImage: "location.fill",
                tone: .secondary,
                density: .compact
            ) {
                Task {
                    let didUpdate = await model.useCurrentLocation()
                    if didUpdate {
                        isPresented = false
                    }
                }
            }
            .disabled(model.isResolvingCurrentLocation)
            .accessibilityIdentifier(LaughTrackViewTestID.homeLocationCurrentButton)

            if model.nearbyPreference != nil {
                LaughTrackButton("Clear location", systemImage: "location.slash", tone: .tertiary, density: .compact) {
                    model.clearNearbyPreference()
                    isPresented = false
                }
                .accessibilityIdentifier(LaughTrackViewTestID.homeLocationClearButton)
            }
        }
    }

    private func applyZip() {
        model.saveNearbyPreference()
        if model.validationMessage == nil {
            isPresented = false
        }
    }

    private func openAppSettings() {
        #if canImport(UIKit)
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
        #endif
    }
}
