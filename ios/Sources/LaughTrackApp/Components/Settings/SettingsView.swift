import SwiftUI
import LaughTrackBridge
import LaughTrackCore

struct SettingsView: View {
    let signedOutMessage: String?
    @ObservedObject var nearbyLocationController: NearbyLocationController

    @Environment(\.appTheme) private var theme
    @StateObject private var model: SettingsNearbyPreferenceModel

    init(
        signedOutMessage: String?,
        nearbyLocationController: NearbyLocationController,
        model: SettingsNearbyPreferenceModel? = nil
    ) {
        self.signedOutMessage = signedOutMessage
        self.nearbyLocationController = nearbyLocationController
        let resolvedModel = model ?? SettingsNearbyPreferenceModel(
            nearbyLocationController: nearbyLocationController
        )
        _model = StateObject(
            wrappedValue: resolvedModel
        )
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Settings",
                    title: "Browse defaults",
                    subtitle: "Saved nearby ZIP, distance, and notification preferences. Account controls live in Profile."
                )

                if let signedOutMessage {
                    LaughTrackAuthMessageCard(message: signedOutMessage)
                }

                nearbyPreferencesSection

                notificationsSection
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, laughTrack.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.settingsScreen)
        .background(laughTrack.colors.canvas.ignoresSafeArea())
        .navigationTitle("Settings")
    }

    private var nearbyPreferencesSection: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Browse",
                title: "Nearby defaults",
                subtitle: "Home and nearby results read from the same saved ZIP code and radius."
            )

            if let preference = model.nearbyPreference {
                LaughTrackCard {
                    VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                        Text("Nearby preference saved")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(
                            preference.source == .manual
                                ? "LaughTrack is using your saved manual nearby preference."
                                : "LaughTrack last saved a nearby preference from your current location."
                        )
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)

                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackBadge("ZIP \(preference.zipCode)", systemImage: "mappin.and.ellipse", tone: .neutral)
                            LaughTrackBadge("\(preference.distanceMiles) mi", systemImage: "location.fill", tone: .highlight)
                            LaughTrackBadge(
                                preference.source == .manual ? "Saved manually" : "Saved from location",
                                systemImage: preference.source == .manual ? "slider.horizontal.3" : "location.north.line",
                                tone: .accent
                            )
                        }
                    }
                }
                .accessibilityIdentifier(LaughTrackViewTestID.settingsNearbySavedState)
            } else {
                LaughTrackStateView(
                    tone: .empty,
                    title: "No nearby preference saved",
                    message: "Save a ZIP code and distance here to reuse the same nearby defaults on home and nearby search."
                )
                .accessibilityIdentifier(LaughTrackViewTestID.settingsNearbyEmptyState)
            }

            LaughTrackCard(tone: .muted) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    Text("Edit nearby preference")
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text("The saved ZIP code and distance below are persisted on this device and used by the nearby sections.")
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.textSecondary)

                    settingsTextField(
                        title: "Saved ZIP code",
                        text: $model.zipCodeDraft
                    )
                        .accessibilityLabel("Saved ZIP code")
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsZipField)

                    VStack(alignment: .leading, spacing: theme.spacing.sm) {
                        Text("Distance")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)

                        Picker("Distance", selection: $model.distanceMiles) {
                            ForEach(SettingsNearbyPreferenceModel.distanceOptions, id: \.self) { distance in
                                Text("\(distance) mi").tag(distance)
                            }
                        }
                        .pickerStyle(.segmented)
                        .accessibilityLabel("Distance")
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsDistancePicker)
                    }

                    if let validationMessage = model.validationMessage {
                        Text(validationMessage)
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.danger)
                    }

                    VStack(spacing: theme.spacing.sm) {
                        LaughTrackButton(
                            "Save nearby preference",
                            systemImage: "square.and.arrow.down"
                        ) {
                            model.saveNearbyPreference()
                        }
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsSaveButton)

                        if model.nearbyPreference != nil {
                            LaughTrackButton(
                                "Clear nearby preference",
                                systemImage: "trash",
                                tone: .destructive
                            ) {
                                model.clearNearbyPreference()
                            }
                            .accessibilityIdentifier(LaughTrackViewTestID.settingsClearButton)
                        }
                    }
                }
            }
        }
    }

    private var notificationsSection: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Notifications",
                title: "No fake alert toggles",
                subtitle: "Push settings only belong here once the iOS app can actually honor them."
            )

            LaughTrackStateView(
                tone: .empty,
                title: "Push notifications are not available yet",
                message: "This build does not deliver push alerts, so Settings intentionally avoids notification switches that would imply working behavior."
            )
        }
    }

    private func settingsTextField(
        title: String,
        text: Binding<String>
    ) -> some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text(title)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)

            TextField(title, text: text)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textPrimary)
                .padding(.horizontal, theme.spacing.md)
                .padding(.vertical, theme.spacing.md)
                .background(laughTrack.colors.surfaceElevated)
                .overlay(
                    RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                        .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        }
    }
}
