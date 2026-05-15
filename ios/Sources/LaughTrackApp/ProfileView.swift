import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct ProfileView: View {
    static let profileSettingsTitle = "Profile settings"
    static let favoriteComedianAlertsTitle = "Favorite comedian alerts"
    static let signOutButtonTitle = "Sign out"
    static let deleteAccountButtonTitle = "Delete account"
    static let signedOutAuthOptions = SignedOutAuthOption.all

    let apiClient: Client
    let signedOutMessage: String?
    let nearbyLocationController: NearbyLocationController

    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.appTheme) private var theme
    @StateObject private var settingsModel: SettingsNearbyPreferenceModel
    @StateObject private var notificationModel: SettingsNotificationPreferenceModel
    @State private var showingDeleteAccountConfirmation = false
    @State private var isDeletingAccount = false
    @State private var deleteAccountErrorMessage: String?

    init(
        apiClient: Client,
        signedOutMessage: String?,
        nearbyLocationController: NearbyLocationController,
        notificationPreferenceStore: NotificationPreferenceStore,
        notificationPreferenceSyncClient: (any NotificationPreferenceSyncing)? = nil,
        profileLocationPreferenceSyncClient: (any ProfileLocationPreferenceSyncing)? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.nearbyLocationController = nearbyLocationController
        _settingsModel = StateObject(
            wrappedValue: SettingsNearbyPreferenceModel(
                nearbyLocationController: nearbyLocationController,
                syncClient: profileLocationPreferenceSyncClient
            )
        )
        _notificationModel = StateObject(
            wrappedValue: SettingsNotificationPreferenceModel(
                store: notificationPreferenceStore,
                syncClient: notificationPreferenceSyncClient
            )
        )
    }

    var body: some View {
        let tokens = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: tokens.spacing.sectionGap) {
                profileHero

                if let session = authManager.currentSession {
                    accountCard(session: session)
                } else {
                    if let signedOutMessage {
                        LaughTrackAuthMessageCard(message: signedOutMessage)
                    }
                }
                if let authenticatedUser = authManager.currentUser {
                    ProfileSettingsSection(
                        authenticatedUser: authenticatedUser,
                        nearbyModel: settingsModel,
                        notificationModel: notificationModel
                    )
                } else {
                    #if DEBUG
                    ProfileSettingsSection(
                        authenticatedUser: AuthenticatedUser(
                            displayName: "Guest preview",
                            email: "design-preview@example.invalid",
                            avatarURL: nil
                        ),
                        nearbyModel: settingsModel,
                        notificationModel: notificationModel
                    )
                    #endif
                }
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, tokens.browseDensity.heroPadding)
            .padding(.bottom, tokens.spacing.sectionGap)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.profileTabScreen)
        .background {
            ZStack(alignment: .top) {
                tokens.colors.canvas.ignoresSafeArea()
                tokens.gradients.heroWash
                    .frame(height: 220)
                    .opacity(0.18)
                    .ignoresSafeArea(edges: .top)
            }
        }
        .navigationTitle("Profile")
        .profileNavigationTitleDisplayMode()
        .modifier(LaughTrackNavigationChrome(background: tokens.colors.canvas))
        .onAppear {
            refreshProfileLocation(from: authManager.currentUser)
            refreshNotificationPreferences(from: authManager.currentUser)
        }
        .onChange(of: authManager.currentUser) { user in
            refreshProfileLocation(from: user)
            refreshNotificationPreferences(from: user)
        }
        .confirmationDialog(
            "Delete your LaughTrack account?",
            isPresented: $showingDeleteAccountConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete account permanently", role: .destructive) {
                Task {
                    await deleteAccount()
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This permanently removes your account and saved favorites. This cannot be undone.")
        }
    }

    private var profileHero: some View {
        let laughTrack = theme.laughTrackTokens
        let isSignedIn = authManager.currentSession != nil

        return LaughTrackCard(tone: .accent, density: .compact) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.tight) {
                HStack(alignment: .center, spacing: theme.spacing.md) {
                    LaughTrackAvatar(
                        style: .url(authManager.currentUser?.avatarURL, fallback: isSignedIn ? "person.crop.circle.fill" : "person.crop.circle.badge.plus"),
                        size: 44,
                        highlighted: true
                    )

                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text(heroTitle)
                            .font(laughTrack.typography.sectionTitle)
                            .foregroundStyle(laughTrack.colors.textInverse)
                            .lineLimit(1)
                            .minimumScaleFactor(0.86)
                            .fixedSize(horizontal: false, vertical: true)

                        Text(heroSubtitle)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textInverse.opacity(0.86))
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if isSignedIn {
                    HStack(spacing: theme.spacing.sm) {
                        LaughTrackBadge("Sync on", systemImage: "checkmark.seal.fill", tone: .highlight)
                        LaughTrackBadge(nearbySummary, systemImage: "location.fill", tone: .accent)
                    }
                } else {
                    VStack(spacing: theme.spacing.sm) {
                        ForEach(Self.signedOutAuthOptions) { option in
                            SignedOutAuthOptionButton(option: option) { provider in
                                Task {
                                    await authManager.signIn(with: provider)
                                }
                            }
                        }
                    }
                }
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.profileHero)
    }

    private var heroTitle: String {
        Self.makeHeroTitle(user: authManager.currentUser, session: authManager.currentSession)
    }

    private var heroSubtitle: String {
        Self.makeHeroSubtitle(user: authManager.currentUser, session: authManager.currentSession)
    }

    // Pure helpers extracted from instance computed properties so ProfileViewTests
    // can verify hero text without HostedView traversal — iOS 26.1+ leaves the
    // SwiftUI accessibility tree unwired in test hosts (TASK-1921), making
    // requireText assertions vacuous.
    static func makeHeroTitle(user: AuthenticatedUser?, session: AuthSessionMetadata?) -> String {
        if let user, let displayName = user.displayName, !displayName.isEmpty {
            return displayName
        }

        if let providerName = session?.provider?.displayName {
            return "\(providerName) account"
        }

        return "Guest mode"
    }

    static func makeHeroSubtitle(user: AuthenticatedUser?, session: AuthSessionMetadata?) -> String {
        if let user, let displayName = user.displayName, !displayName.isEmpty {
            return "Favorites sync is on for \(displayName)."
        }

        if let providerName = session?.provider?.displayName {
            return "Favorites sync through \(providerName) is on."
        }

        return "Sign in to sync favorites and recover your account."
    }

    private var nearbySummary: String {
        guard let preference = settingsModel.nearbyPreference else {
            return "No nearby default"
        }

        return "\(preference.zipCode) · \(preference.distanceMiles) mi"
    }

    private func refreshNotificationPreferences(from user: AuthenticatedUser?) {
        guard let user else { return }
        notificationModel.replaceServerBackedPreferences(from: user)
    }

    private func refreshProfileLocation(from user: AuthenticatedUser?) {
        guard let user else { return }
        settingsModel.replaceServerBackedPreference(from: user)
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

        LaughTrackCard(tone: .standard) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.clusterGap) {
                LaughTrackSectionHeader(
                    eyebrow: "Account",
                    title: "Signed-in profile",
                    subtitle: "Your app session and provider details.",
                    density: .compact
                )

                HStack(alignment: .top, spacing: laughTrack.spacing.itemGap) {
                    LaughTrackAvatar(
                        style: .url(user?.avatarURL, fallback: providerSymbol),
                        highlighted: true
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
                    Self.signOutButtonTitle,
                    systemImage: "rectangle.portrait.and.arrow.right",
                    tone: .destructive
                ) {
                    Task {
                        await authManager.signOut()
                    }
                }

                LaughTrackButton(
                    Self.deleteAccountButtonTitle,
                    systemImage: "trash",
                    tone: .destructive
                ) {
                    showingDeleteAccountConfirmation = true
                }
                .disabled(isDeletingAccount)
                .accessibilityIdentifier(LaughTrackViewTestID.profileDeleteAccountButton)

                if let deleteAccountErrorMessage {
                    Text(deleteAccountErrorMessage)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.danger)
                }
            }
        }
    }

    private func deleteAccount() async {
        guard !isDeletingAccount else { return }
        isDeletingAccount = true
        deleteAccountErrorMessage = nil
        defer { isDeletingAccount = false }

        do {
            try await authManager.deleteAccount()
        } catch {
            deleteAccountErrorMessage = "Could not delete your account. Please try again."
        }
    }

}

private extension View {
    @ViewBuilder
    func profileNavigationTitleDisplayMode() -> some View {
        #if os(iOS)
        navigationBarTitleDisplayMode(.inline)
        #else
        self
        #endif
    }
}

private struct ProfileSettingsSection: View {
    let authenticatedUser: AuthenticatedUser
    @ObservedObject var nearbyModel: SettingsNearbyPreferenceModel
    @ObservedObject var notificationModel: SettingsNotificationPreferenceModel

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.sectionGap) {
            LaughTrackSectionHeader(
                eyebrow: "Profile",
                title: ProfileView.profileSettingsTitle,
                subtitle: "Location and alert preferences saved to your account."
            )

            ProfileNearbyPreferencesSection(model: nearbyModel)
            ProfileNotificationsSection(
                emailAddress: authenticatedUser.email,
                model: notificationModel
            )
        }
        .accessibilityIdentifier(LaughTrackViewTestID.profileSettingsPanel)
    }
}

private struct ProfileNearbyPreferencesSection: View {
    @ObservedObject var model: SettingsNearbyPreferenceModel

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Location",
                title: "Profile location",
                subtitle: "Set the location Near Me reads from your profile."
            )

            editorCard
        }
    }

    private var editorCard: some View {
        let laughTrack = theme.laughTrackTokens

        return LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                Text("Near Me profile location")
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)

                Text(locationSummary)
                .font(laughTrack.typography.body)
                .foregroundStyle(laughTrack.colors.textSecondary)

                LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft) {
                    Button {
                        model.saveNearbyPreference()
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
                .onSubmit {
                    model.saveNearbyPreference()
                }
                .accessibilityLabel("Profile location ZIP code")
                .accessibilityIdentifier(LaughTrackViewTestID.settingsZipField)

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    Text("Distance")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .textCase(.uppercase)

                    distancePicker
                }

                VStack(spacing: theme.spacing.sm) {
                    LaughTrackButton(
                        "Save profile location",
                        systemImage: "square.and.arrow.down"
                    ) {
                        model.saveNearbyPreference()
                    }
                    .accessibilityIdentifier(LaughTrackViewTestID.settingsSaveButton)

                    LaughTrackButton(
                        model.isResolvingCurrentLocation ? "Finding ZIP..." : "Current location",
                        systemImage: "location.fill",
                        tone: .secondary
                    ) {
                        Task {
                            _ = await model.useCurrentLocation()
                        }
                    }
                    .disabled(model.isResolvingCurrentLocation)

                    if model.nearbyPreference != nil {
                        LaughTrackButton(
                            "Clear profile location",
                            systemImage: "location.slash",
                            tone: .tertiary
                        ) {
                            model.clearNearbyPreference()
                        }
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsClearButton)
                    }
                }

                if let validationMessage = model.validationMessage {
                    Text(validationMessage)
                        .font(laughTrack.typography.body)
                        .foregroundStyle(laughTrack.colors.danger)
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
        }
        .accessibilityIdentifier(model.nearbyPreference == nil
            ? LaughTrackViewTestID.settingsNearbyEmptyState
            : LaughTrackViewTestID.settingsNearbySavedState
        )
    }

    private var distancePicker: some View {
        Picker("Distance", selection: $model.distanceMiles) {
            ForEach(SettingsNearbyPreferenceModel.distanceOptions, id: \.self) { distance in
                Text("\(distance) mi").tag(distance)
            }
        }
        .pickerStyle(.segmented)
        .accessibilityLabel("Distance")
        .accessibilityIdentifier(LaughTrackViewTestID.settingsDistancePicker)
    }

    private var locationSummary: String {
        guard let preference = model.nearbyPreference else {
            return "No profile location is saved. Enter a ZIP or use current location to power Near Me."
        }

        if let city = preference.city, let state = preference.state {
            return "Near Me is using \(city), \(state) from your profile."
        }

        return "Near Me is using ZIP \(preference.zipCode) from your profile."
    }
}

private struct ProfileNotificationsSection: View {
    let emailAddress: String
    @ObservedObject var model: SettingsNotificationPreferenceModel

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
            LaughTrackSectionHeader(
                eyebrow: "Notifications",
                title: ProfileView.favoriteComedianAlertsTitle,
                subtitle: "Choose how LaughTrack should notify you when saved comedians add shows."
            )

            LaughTrackCard(tone: .muted) {
                VStack(alignment: .leading, spacing: laughTrack.spacing.itemGap) {
                    VStack(spacing: theme.spacing.sm) {
                        notificationToggle(
                            title: "Email",
                            subtitle: "New-show alerts sent to \(emailAddress).",
                            systemImage: "envelope.fill",
                            isOn: Binding(
                                get: { model.preferences.favoriteComedianEmailAlertsEnabled },
                                set: { model.setFavoriteComedianEmailAlertsEnabled($0) }
                            )
                        )
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsFavoriteComedianEmailAlertsToggle)

                        Divider()
                            .overlay(laughTrack.colors.borderSubtle)

                        notificationToggle(
                            title: "Push notifications",
                            subtitle: "New-show alerts delivered on this device.",
                            systemImage: "bell.badge.fill",
                            isOn: Binding(
                                get: { model.preferences.favoriteComedianPushAlertsEnabled },
                                set: { model.setFavoriteComedianPushAlertsEnabled($0) }
                            )
                        )
                        .accessibilityIdentifier(LaughTrackViewTestID.settingsFavoriteComedianPushAlertsToggle)
                    }

                    Text("Alert preferences are saved to your profile.")
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)

                    if let syncMessage = model.syncMessage {
                        Text(syncMessage)
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.danger)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.settingsNotificationsSection)
    }

    private func notificationToggle(
        title: String,
        subtitle: String,
        systemImage: String,
        isOn: Binding<Bool>,
        isEnabled: Bool = true
    ) -> some View {
        let laughTrack = theme.laughTrackTokens

        return Toggle(isOn: isOn) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                Image(systemName: systemImage)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(isEnabled ? laughTrack.colors.accent : laughTrack.colors.textSecondary.opacity(0.7))
                    .frame(width: 28)

                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text(title)
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text(subtitle)
                        .font(laughTrack.typography.metadata)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .toggleStyle(.switch)
        .tint(laughTrack.colors.accent)
        .disabled(!isEnabled)
        .opacity(isEnabled ? 1 : 0.68)
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
