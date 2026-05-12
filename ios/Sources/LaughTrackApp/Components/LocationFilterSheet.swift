import SwiftUI
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

/// Sheet used wherever the app asks the user to pick a search location —
/// search-tab location pill and any future "near me" affordance. Mirrors the
/// chrome of `DateRangeFilterSheet`: titled header with close button, content
/// region in the middle, and a primary/secondary/tertiary `LaughTrackButton`
/// stack at the bottom. Callers bind the `ShowsListModel` whose nearby
/// preference state the sheet edits.
struct LocationFilterSheet: View {
    @ObservedObject var model: ShowsListModel
    @Binding var isPresented: Bool
    var title: String = "Location"
    var subtitle: String = "Set the location used for nearby shows."

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text(title)
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text(subtitle)
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                }

                Spacer(minLength: 0)

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: theme.iconSizes.sm, weight: .bold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .frame(width: 36, height: 36)
                        .background(laughTrack.colors.surfaceElevated)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close")
            }

            LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft) {
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

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton("Apply", systemImage: "checkmark", density: .compact) {
                    applyZip()
                }

                LaughTrackButton(
                    model.isResolvingCurrentLocation ? "Finding ZIP..." : "Use my location",
                    systemImage: "location.fill",
                    tone: .secondary,
                    density: .compact
                ) {
                    Task {
                        let didResolve = await model.useCurrentLocation()
                        if didResolve {
                            isPresented = false
                        }
                    }
                }
                .disabled(model.isResolvingCurrentLocation)

                if model.activeNearbyPreference != nil {
                    LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact) {
                        model.clearLocation()
                        isPresented = false
                    }
                }
            }

            if let nearbyStatusMessage = model.nearbyStatusMessage {
                InlineStatusMessage(message: nearbyStatusMessage)

                if nearbyStatusMessage == NearbyLocationError.denied.recoveryMessage {
                    LaughTrackButton("Open Settings", systemImage: "gearshape", tone: .secondary, density: .compact, fullWidth: false) {
                        openAppSettings()
                    }
                }
            }

            Spacer(minLength: 0)
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .presentationDetents([.medium, .large])
    }

    private func applyZip() {
        if model.applyManualZip() {
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
