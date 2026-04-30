import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct ProfileView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let nearbyLocationController: NearbyLocationController

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @StateObject private var settingsModel: SettingsNearbyPreferenceModel

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.nearbyLocationController = nearbyLocationController
        _settingsModel = StateObject(
            wrappedValue: SettingsNearbyPreferenceModel(
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.browseDensity.shelfGap) {
                if let session = authManager.currentSession {
                    accountCard(session: session)
                } else {
                    if let signedOutMessage {
                        LaughTrackAuthMessageCard(message: signedOutMessage)
                    }
                    signInCTASection
                }
                ProfileSettingsSection(
                    signedOutMessage: signedOutMessage,
                    model: settingsModel
                )
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.vertical, tokens.browseDensity.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.profileTabScreen)
        .background(tokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Profile")
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
    }

    @ViewBuilder
    private func accountCard(session: AuthSessionMetadata) -> some View {
        let laughTrack = theme.laughTrackTokens
        let user = authManager.currentUser
        let providerSymbol = session.provider?.symbolName ?? "person.crop.circle"
        let providerName = session.provider?.displayName ?? "Saved session"
        let primaryName: String = {
            if let displayName = user?.displayName, !displayName.isEmpty {
                return displayName
            }
            return providerName
        }()

        LaughTrackCard {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                HStack(alignment: .top, spacing: laughTrack.spacing.itemGap) {
                    LaughTrackAvatar(
                        style: .url(user?.avatarURL, fallback: providerSymbol)
                    )

                    VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                        Text(primaryName)
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        if let email = user?.email {
                            Text(email)
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                        } else {
                            Text(
                                session.expiresAt.map {
                                    "Session expires \($0.formatted(.dateTime.month().day().hour().minute()))."
                                } ?? "Session expiration is not available."
                            )
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                        }
                    }
                }

                LaughTrackButton(
                    "Sign out",
                    systemImage: "rectangle.portrait.and.arrow.right",
                    tone: .destructive
                ) {
                    Task {
                        await authManager.signOut()
                    }
                }
            }
        }
    }

    private var signInCTASection: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Sign in",
                title: "Save favorites across sessions",
                subtitle: "Sign in when you want synced favorite comedians and recovery messaging tied to a real account."
            )

            LaughTrackButton(
                "Sign in",
                systemImage: "person.crop.circle.badge.plus",
                tone: .primary
            ) {
                loginModalPresenter.present()
            }
        }
    }
}

private struct ProfileSettingsSection: View {
    let signedOutMessage: String?
    @ObservedObject var model: SettingsNearbyPreferenceModel

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
            LaughTrackSectionHeader(
                eyebrow: "Settings",
                title: "Browse defaults",
                subtitle: "Saved nearby ZIP, distance, and notification preferences."
            )

            if let signedOutMessage {
                LaughTrackAuthMessageCard(message: signedOutMessage)
            }

            ProfileNearbyPreferencesSection(model: model)
            ProfileNotificationsSection()
        }
    }
}

private struct ProfileNearbyPreferencesSection: View {
    @ObservedObject var model: SettingsNearbyPreferenceModel

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Browse",
                title: "Nearby defaults",
                subtitle: "Near Me and nearby results read from the same saved ZIP code and radius."
            )

            if let preference = model.nearbyPreference {
                savedPreferenceCard(preference)
            } else {
                LaughTrackStateView(
                    tone: .empty,
                    title: "No nearby preference saved",
                    message: "Save a ZIP code and distance here to reuse the same nearby defaults on home and nearby search."
                )
                .accessibilityIdentifier(LaughTrackViewTestID.settingsNearbyEmptyState)
            }

            editorCard
        }
    }

    private func savedPreferenceCard(_ preference: NearbyPreference) -> some View {
        let laughTrack = theme.laughTrackTokens

        return LaughTrackCard {
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
    }

    private var editorCard: some View {
        let laughTrack = theme.laughTrackTokens

        return LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                Text("Edit nearby preference")
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)

                Text("The saved ZIP code and distance below are persisted on this device and used by the nearby sections.")
                    .font(laughTrack.typography.body)
                    .foregroundStyle(laughTrack.colors.textSecondary)

                ProfileSettingsTextField(
                    title: "Saved ZIP code",
                    text: $model.zipCodeDraft
                )
                .accessibilityLabel("Saved ZIP code")
                .accessibilityIdentifier(LaughTrackViewTestID.settingsZipField)

                distancePicker

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

    private var distancePicker: some View {
        let laughTrack = theme.laughTrackTokens

        return VStack(alignment: .leading, spacing: theme.spacing.sm) {
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
    }
}

private struct ProfileNotificationsSection: View {
    @Environment(\.appTheme) private var theme

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Notifications",
                title: "No fake alert toggles",
                subtitle: "Push settings only belong here once the iOS app can actually honor them."
            )

            LaughTrackStateView(
                tone: .empty,
                title: "Push notifications are not available yet",
                message: "This build does not deliver push alerts, so LaughTrack intentionally avoids notification switches that would imply working behavior."
            )
        }
    }
}

private struct ProfileSettingsTextField: View {
    let title: String
    @Binding var text: String

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text(title)
                .font(laughTrack.typography.metadata)
                .foregroundStyle(laughTrack.colors.textSecondary)
                .textCase(.uppercase)

            TextField(title, text: $text)
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
