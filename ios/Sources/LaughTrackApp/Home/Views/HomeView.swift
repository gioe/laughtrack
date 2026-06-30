import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum HomeContentSection: Equatable {
    case showsTonight
    case thisWeek
    case comedians
    case clubs
    case podcasts

    static func sections(for primitive: SearchRootModel.Pivot?) -> [HomeContentSection] {
        switch primitive {
        case .shows:
            return [.showsTonight, .thisWeek]
        case .comedians:
            return [.comedians]
        case .clubs:
            return [.clubs]
        case .podcasts:
            return [.podcasts]
        default:
            return [.showsTonight, .thisWeek, .comedians, .clubs, .podcasts]
        }
    }
}

enum HomeShowRailKind: Equatable {
    case showsTonight
    case thisWeek

    var eyebrow: String? {
        switch self {
        case .showsTonight:
            // The Tonight hero cards already lead with a big "TONIGHT!"
            // marquee banner, so the shelf eyebrow would just duplicate it.
            return nil
        case .thisWeek:
            return "Coming Up"
        }
    }

    var title: String? {
        switch self {
        case .showsTonight:
            return nil
        case .thisWeek:
            return "Best shows this week"
        }
    }

    var subtitle: String? {
        switch self {
        case .showsTonight:
            return nil
        case .thisWeek:
            return nil
        }
    }

    var emptyMessage: String {
        switch self {
        case .showsTonight:
            return "No shows are listed for tonight yet."
        case .thisWeek:
            return "No upcoming shows are listed near you this week."
        }
    }

    var searchShortcut: String? {
        switch self {
        case .showsTonight:
            return "Tonight"
        case .thisWeek:
            return "This Week"
        }
    }

    var railAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightRail
        case .thisWeek:
            return "laughtrack.home.this-week-rail"
        }
    }

    var seeMoreAccessibilityIdentifier: String {
        switch self {
        case .showsTonight:
            return LaughTrackViewTestID.homeShowsTonightSeeMoreButton
        case .thisWeek:
            return "laughtrack.home.this-week-see-more-button"
        }
    }
}

struct HomeView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let selectedPrimitive: SearchRootModel.Pivot?
    let searchNavigationBridge: SearchNavigationBridge
    let onInitialHomeLoadComplete: (() -> Void)?

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastPlayer: PodcastPlaybackController
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    init(
        apiClient: Client,
        signedOutMessage: String?,
        selectedPrimitive: SearchRootModel.Pivot? = nil,
        searchNavigationBridge: SearchNavigationBridge,
        onInitialHomeLoadComplete: (() -> Void)? = nil
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.selectedPrimitive = selectedPrimitive
        self.searchNavigationBridge = searchNavigationBridge
        self.onInitialHomeLoadComplete = onInitialHomeLoadComplete
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: laughTrack.browseDensity.shelfGap) {
                HomeDiscoverHeader(
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self),
                    nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
                    profileLocationPreferenceSyncClient: serviceContainer.resolveOptional((any ProfileLocationPreferenceSyncing).self),
                    currentUser: authManager.currentUser
                )

                contentSections
            }
            .padding(.horizontal, theme.spacing.lg)
            .padding(.top, theme.spacing.sm)
            .padding(.bottom, laughTrack.browseDensity.heroPadding)
        }
        .rootScrollBottomClearance(
            theme: theme,
            isPodcastMiniPlayerVisible: podcastPlayer.currentItem != nil
        )
        .accessibilityIdentifier(LaughTrackViewTestID.homeScreen)
        .background(Color.clear)
        .navigationTitle("LaughTrack")
        .toolbar {
            ToolbarItem(placement: toolbarPlacement) {
                Button {
                    coordinator.push(AppRoute.nearMeToolbarTarget(isSignedIn: authManager.currentSession != nil))
                } label: {
                    Image(systemName: authManager.currentSession == nil ? "person.crop.circle.badge.plus" : "person.crop.circle")
                }
                .accessibilityLabel(authManager.currentSession == nil ? "Sign in" : "Profile")
                .accessibilityIdentifier(LaughTrackViewTestID.homeSettingsButton)
            }
        }
        .modifier(LaughTrackNavigationChrome(background: .clear))
    }

    private var toolbarPlacement: ToolbarItemPlacement {
        #if os(iOS)
        .topBarTrailing
        #else
        .primaryAction
        #endif
    }

    @ViewBuilder
    private var contentSections: some View {
        ForEach(HomeContentSection.sections(for: selectedPrimitive), id: \.self) { section in
            switch section {
            case .showsTonight:
                showsSection(.showsTonight)
            case .thisWeek:
                showsSection(.thisWeek)
            case .comedians:
                comediansSection
            case .clubs:
                clubsSection
            case .podcasts:
                podcastsSection
            }
        }
    }

    private func showsSection(_ railKind: HomeShowRailKind) -> some View {
        HomeShowsTonightRail(
            railKind: railKind,
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            searchNavigationBridge: searchNavigationBridge,
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self),
            onInitialHomeLoadComplete: onInitialHomeLoadComplete
        )
    }

    private var comediansSection: some View {
        HomeTrendingComediansRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var clubsSection: some View {
        HomePopularClubsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }

    private var podcastsSection: some View {
        HomeTrendingPodcastsRail(
            apiClient: apiClient,
            nearbyPreferenceStore: serviceContainer.resolve(NearbyPreferenceStore.self),
            cache: serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self),
            persistentCache: serviceContainer.resolve(PersistentMainPageCache.self)
        )
    }
}

struct LaughTrackAtmosphereBackground: View {
    @Environment(\.appTheme) private var theme
    private let spotlightHue = Color(red: 1.0, green: 0.72, blue: 0.30)

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            laughTrack.colors.canvas

            RadialGradient(
                colors: [
                    spotlightHue.opacity(0.30),
                    laughTrack.colors.accentStrong.opacity(0.18),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: .topLeading,
                startRadius: 0,
                endRadius: 430
            )

            LinearGradient(
                colors: [
                    spotlightHue.opacity(0.22),
                    laughTrack.colors.heroEnd.opacity(0.20),
                    laughTrack.colors.accentMuted.opacity(0.10),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                startPoint: .topLeading,
                endPoint: UnitPoint(x: 0.72, y: 0.46)
            )

            RadialGradient(
                colors: [
                    laughTrack.colors.accentStrong.opacity(0.24),
                    laughTrack.colors.accentMuted.opacity(0.08),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: UnitPoint(x: 0.72, y: 0.08),
                startRadius: 18,
                endRadius: 300
            )

            RadialGradient(
                colors: [
                    Color(red: 0.34, green: 0.04, blue: 0.07).opacity(0.24),
                    laughTrack.colors.canvas.opacity(0.0),
                ],
                center: UnitPoint(x: 0.05, y: 0.56),
                startRadius: 36,
                endRadius: 360
            )
        }
    }
}

private enum HomeDiscoverRailVariant {
    case spotlight
    case scheduleBoard
    case posterGrid
    case listeningRoom

    var topGlowAlignment: UnitPoint {
        switch self {
        case .spotlight:
            return UnitPoint(x: 0.5, y: 0.0)
        case .scheduleBoard:
            return UnitPoint(x: 0.14, y: 0.0)
        case .posterGrid:
            return UnitPoint(x: 0.78, y: 0.02)
        case .listeningRoom:
            return UnitPoint(x: 0.5, y: 0.12)
        }
    }

    var surfaceOpacity: Double {
        switch self {
        case .spotlight:
            return 0.70
        case .scheduleBoard:
            return 0.78
        case .posterGrid:
            return 0.74
        case .listeningRoom:
            return 0.70
        }
    }

    var glowOpacity: Double {
        switch self {
        case .spotlight:
            return 0.24
        case .scheduleBoard:
            return 0.16
        case .posterGrid:
            return 0.18
        case .listeningRoom:
            return 0.14
        }
    }
}

private struct HomeDiscoverRailCard<Content: View>: View {
    let variant: HomeDiscoverRailVariant
    let eyebrow: String?
    let title: String?
    let subtitle: String?
    let accessibilityIdentifier: String?
    @ViewBuilder let content: Content

    @Environment(\.appTheme) private var theme

    init(
        variant: HomeDiscoverRailVariant,
        eyebrow: String? = nil,
        title: String? = nil,
        subtitle: String? = nil,
        accessibilityIdentifier: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.variant = variant
        self.eyebrow = eyebrow
        self.title = title
        self.subtitle = subtitle
        self.accessibilityIdentifier = accessibilityIdentifier
        self.content = content()
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.md) {
            if let title {
                HomeDiscoverSectionHeader(
                    eyebrow: eyebrow,
                    title: title,
                    subtitle: subtitle
                )
                .modifier(HomeRailAccessibilityIdentifierModifier(identifier: accessibilityIdentifier))
            }

            content
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(railBackground)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.accentMuted.opacity(0.34), lineWidth: 1)
        )
        .overlay(alignment: .topLeading) {
            Capsule(style: .continuous)
                .fill(laughTrack.colors.accentStrong.opacity(0.72))
                .frame(width: 52, height: 2)
                .padding(.leading, laughTrack.browseDensity.compactCardPadding)
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.44), radius: 8)
        }
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .modifier(HomeRailAccessibilityIdentifierModifier(
            identifier: title == nil ? accessibilityIdentifier : nil
        ))
    }

    private var railBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.surfaceElevated.opacity(variant.surfaceOpacity)

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(variant.glowOpacity),
                    laughTrack.colors.accentMuted.opacity(variant.glowOpacity * 0.35),
                    laughTrack.colors.surface.opacity(0.0),
                ],
                center: variant.topGlowAlignment,
                startRadius: 12,
                endRadius: 240
            )

            LinearGradient(
                colors: [
                    Color.white.opacity(0.035),
                    Color.black.opacity(0.10),
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }
}

private struct HomeRailAccessibilityIdentifierModifier: ViewModifier {
    let identifier: String?

    func body(content: Content) -> some View {
        if let identifier {
            content.accessibilityIdentifier(identifier)
        } else {
            content
        }
    }
}

private struct HomeDiscoverSectionHeader: View {
    let eyebrow: String?
    let title: String
    let subtitle: String?

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: 7) {
            if let eyebrow {
                Text(eyebrow)
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .tracking(2.0)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .lineLimit(1)
            }

            HStack(alignment: .firstTextBaseline, spacing: theme.spacing.sm) {
                Text(title)
                    .font(.system(size: 22, weight: .heavy, design: .rounded))
                    .tracking(0.3)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 0)

                HStack(spacing: 4) {
                    ForEach(0..<5, id: \.self) { index in
                        Circle()
                            .fill(laughTrack.colors.accentStrong.opacity(0.85 - Double(index) * 0.11))
                            .frame(width: 4, height: 4)
                            .shadow(color: laughTrack.colors.accentStrong.opacity(0.34), radius: 4)
                    }
                }
                .accessibilityHidden(true)
            }

            if let subtitle {
                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

struct HomeMarqueeStageBackground: View {
    var glowRadius: CGFloat = 140
    var glowOpacity: Double = 0.22

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            laughTrack.colors.heroStart

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(glowOpacity),
                    laughTrack.colors.accent.opacity(0.0)
                ],
                center: .center,
                startRadius: 12,
                endRadius: glowRadius
            )
        }
        .mask(
            LinearGradient(
                stops: [
                    .init(color: .black.opacity(0), location: 0),
                    .init(color: .black.opacity(0.5), location: 0.06),
                    .init(color: .black, location: 0.16),
                    .init(color: .black, location: 0.84),
                    .init(color: .black.opacity(0.5), location: 0.94),
                    .init(color: .black.opacity(0), location: 1)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }
}

private struct HomeBulbFrame: View {
    var width: CGFloat
    var height: CGFloat
    var cornerRadius: CGFloat
    var isCircle = false
    var lineWidth: CGFloat = 2
    var dash: [CGFloat] = [0.5, 6]
    var bulbColor: Color? = nil

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let resolvedBulbColor = bulbColor ?? laughTrack.colors.accentStrong
        let stroke = StrokeStyle(
            lineWidth: lineWidth,
            lineCap: .round,
            lineJoin: .round,
            dash: dash
        )

        Group {
            if isCircle {
                Circle()
                    .strokeBorder(resolvedBulbColor, style: stroke)
            } else {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(resolvedBulbColor, style: stroke)
            }
        }
        .frame(width: width, height: height)
        .shadow(color: resolvedBulbColor.opacity(0.70), radius: 4)
        .shadow(color: resolvedBulbColor.opacity(0.34), radius: 9)
    }
}

private struct HomeDiscoverHeader: View {
    @ObservedObject private var nearbyLocationController: NearbyLocationController
    @ObservedObject private var nearbyPreferenceStore: NearbyPreferenceStore
    @StateObject private var locationModel: SettingsNearbyPreferenceModel
    @State private var isLocationEditorPresented = false
    private let currentUser: AuthenticatedUser?

    @Environment(\.appTheme) private var theme

    init(
        nearbyLocationController: NearbyLocationController,
        nearbyPreferenceStore: NearbyPreferenceStore,
        profileLocationPreferenceSyncClient: (any ProfileLocationPreferenceSyncing)?,
        currentUser: AuthenticatedUser?
    ) {
        self.nearbyLocationController = nearbyLocationController
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.currentUser = currentUser
        _locationModel = StateObject(
            wrappedValue: SettingsNearbyPreferenceModel(
                nearbyLocationController: nearbyLocationController,
                syncClient: profileLocationPreferenceSyncClient
            )
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            Button {
                isLocationEditorPresented = true
            } label: {
                HomeLocationPrompt(
                    displayPreference: nearbyLocationController.preference ?? nearbyPreferenceStore.defaultPreference,
                    isExplicitPreference: nearbyLocationController.preference != nil
                )
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier(LaughTrackViewTestID.homeLocationPrompt)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .sheet(isPresented: $isLocationEditorPresented) {
            HomeLocationEditorSheet(
                model: locationModel,
                isPresented: $isLocationEditorPresented
            )
            .environment(\.appTheme, theme)
        }
        .onAppear {
            refreshProfileLocation(from: currentUser)
        }
        .onChange(of: currentUser) { user in
            refreshProfileLocation(from: user)
        }
    }

    private func refreshProfileLocation(from user: AuthenticatedUser?) {
        guard let user else { return }
        locationModel.replaceServerBackedPreference(from: user)
    }
}

private struct HomeLocationPrompt: View {
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

private struct HomeLocationEditorSheet: View {
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

private struct HomeShowsTonightRail: View {
    let railKind: HomeShowRailKind
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let searchNavigationBridge: SearchNavigationBridge
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache
    let onInitialHomeLoadComplete: (() -> Void)?

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeShowsTonightModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: railKind == .showsTonight ? .spotlight : .scheduleBoard,
            eyebrow: railKind.eyebrow,
            title: title,
            subtitle: railKind.subtitle,
            accessibilityIdentifier: railKind.railAccessibilityIdentifier
        ) {
            switch model.phase {
            case .idle, .loading:
                ShowsListSkeleton(rowCount: 3)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            railKind: railKind,
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let shows):
                if shows.isEmpty {
                    EmptyCard(message: railKind.emptyMessage)
                } else {
                    showsContent(shows)
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles, railKind: railKind)) {
            await model.refresh(
                railKind: railKind,
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
            if railKind == .showsTonight {
                nearbyPreferenceStore.setDefaultPreference(model.feedNearbyPreference)
            }
        }
        .task(id: hasFinishedInitialLoad) {
            guard railKind == .showsTonight, hasFinishedInitialLoad else { return }
            onInitialHomeLoadComplete?()
        }
    }

    private var title: String? {
        railKind.title
    }

    private var hasFinishedInitialLoad: Bool {
        switch model.phase {
        case .idle, .loading:
            return false
        case .success, .failure:
            return true
        }
    }

    @ViewBuilder
    private func showsContent(_ shows: [Components.Schemas.Show]) -> some View {
        if railKind == .showsTonight {
            HomeShowsTonightCarousel(shows: shows)
        } else {
            VStack(spacing: theme.spacing.sm) {
                ForEach(shows, id: \.id) { show in
                    Button {
                        coordinator.open(.show(show.id))
                    } label: {
                        ShowRow(show: show, presentation: .compactTicket)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightButton(show.id))
                }
            }
        }

        LaughTrackButton("See more", systemImage: "magnifyingglass", tone: .secondary, density: .compact) {
            searchNavigationBridge.openSearch(
                HomeShowsTonightModel.seeMoreSearchSeed(
                    railKind: railKind,
                    nearbyPreference: seeMoreNearbyPreference
                )
            )
        }
        .accessibilityIdentifier(railKind.seeMoreAccessibilityIdentifier)
    }

    private var seeMoreNearbyPreference: NearbyPreference? {
        nearbyPreferenceStore.preference ?? model.feedNearbyPreference
    }
}

private struct HomeShowsTonightCarousel: View {
    let shows: [Components.Schemas.Show]

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme
    @State private var selectedShowID: Int?

    var body: some View {
        #if os(iOS)
        VStack(spacing: theme.spacing.xs) {
            GeometryReader { proxy in
                let pageWidth = min(proxy.size.width, max(0, UIScreen.main.bounds.width - 64))

                HStack(spacing: 0) {
                    carouselButtons(pageWidth: pageWidth)
                }
                .offset(x: -CGFloat(selectedShowIndex) * pageWidth)
                .animation(.snappy(duration: 0.25), value: selectedShowIndex)
                .frame(width: pageWidth, alignment: .leading)
                .clipped()
                .highPriorityGesture(pagerDragGesture(pageWidth: pageWidth))
            }
            .frame(height: 456)
        }
        #else
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: theme.spacing.sm) {
                carouselButtons(pageWidth: 320)
                    .frame(width: 320)
            }
        }
        #endif
    }

    private func carouselButtons(pageWidth: CGFloat) -> some View {
        ForEach(shows, id: \.id) { show in
            Button {
                coordinator.open(.show(show.id))
            } label: {
                HomeShowsTonightHeroCard(
                    show: show,
                    width: pageWidth,
                    pageIndicatorCount: shows.count,
                    selectedPageIndex: selectedShowIndex
                )
                    .frame(width: pageWidth)
            }
            .frame(width: pageWidth)
            .clipped()
            .buttonStyle(.plain)
            .accessibilityIdentifier(show.id == shows.first?.id ? LaughTrackViewTestID.homeShowsTonightHeroButton : LaughTrackViewTestID.homeShowsTonightButton(show.id))
            .tag(show.id)
        }
    }

    private var selectedShowIndex: Int {
        guard let selectedID = selectedShowID ?? shows.first?.id,
              let index = shows.firstIndex(where: { $0.id == selectedID })
        else {
            return 0
        }

        return index
    }

    private func pagerDragGesture(pageWidth: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 20)
            .onEnded { value in
                let nextIndex = HomeHorizontalPagerDrag.nextIndex(
                    currentIndex: selectedShowIndex,
                    itemCount: shows.count,
                    pageWidth: pageWidth,
                    translation: value.translation
                )
                selectedShowID = shows[nextIndex].id
            }
    }
}

enum HomeHorizontalPagerDrag {
    static func nextIndex(
        currentIndex: Int,
        itemCount: Int,
        pageWidth: CGFloat,
        translation: CGSize
    ) -> Int {
        guard itemCount > 0 else { return 0 }
        let safeCurrentIndex = max(0, min(currentIndex, itemCount - 1))
        guard abs(translation.width) > abs(translation.height) else {
            return safeCurrentIndex
        }

        let threshold = pageWidth * 0.2
        if translation.width < -threshold {
            return min(itemCount - 1, safeCurrentIndex + 1)
        }
        if translation.width > threshold {
            return max(0, safeCurrentIndex - 1)
        }
        return safeCurrentIndex
    }
}

private struct HomeShowsTonightPageIndicator: View {
    let count: Int
    let selectedIndex: Int

    @Environment(\.appTheme) private var theme

    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<count, id: \.self) { index in
                Circle()
                    .fill(
                        index == selectedIndex
                            ? theme.laughTrackTokens.colors.textPrimary
                            : theme.laughTrackTokens.colors.textSecondary.opacity(0.45)
                    )
                    .frame(width: 7, height: 7)
            }
        }
        .frame(height: count > 1 ? 12 : 0)
        .opacity(count > 1 ? 1 : 0)
        .accessibilityHidden(true)
    }
}

private struct HomeShowsTonightHeroCard: View {
    let show: Components.Schemas.Show
    var width: CGFloat?
    var pageIndicatorCount = 0
    var selectedPageIndex = 0

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .center, spacing: theme.spacing.md) {
            Text("TONIGHT!")
                .font(.system(size: 22, weight: .heavy, design: .rounded))
                .tracking(2.4)
                .textCase(.uppercase)
                .foregroundStyle(laughTrack.colors.accentStrong)
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.4), radius: 6)

            artwork

            VStack(alignment: .center, spacing: 10) {
                Text(timeLabel)
                    .font(.system(size: 30, weight: .heavy, design: .rounded))
                    .tracking(0.5)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(1)
                    .shadow(color: .black.opacity(0.35), radius: 2, y: 1)

                Text(ShowTitlePresentation.title(for: show))
                    .font(.system(size: 16, weight: .heavy, design: .rounded))
                    .tracking(0.4)
                    .textCase(.uppercase)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Text(venueLine)
                    .font(.system(size: 9, weight: .semibold, design: .rounded))
                    .tracking(2)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
                    .fixedSize(horizontal: false, vertical: true)

                if let priceLabel {
                    Text(priceLabel)
                        .font(laughTrack.typography.body.weight(.heavy))
                        .foregroundStyle(Color.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 5)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(Capsule(style: .continuous))
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.45), radius: 6, y: 2)
                        .padding(.top, 4)
                }

                HomeShowsTonightPageIndicator(
                    count: pageIndicatorCount,
                    selectedIndex: selectedPageIndex
                )
            }
            .frame(maxWidth: .infinity)
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .frame(width: width, alignment: .leading)
        .background(laughTrack.colors.surface)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(ShowTitlePresentation.title(for: show)), \(show.clubName ?? "Unknown club"), \(accessibilityMetadata.joined(separator: ", "))")
    }

    private static let stageHeight: CGFloat = 198

    @ViewBuilder
    private var artwork: some View {
        GeometryReader { proxy in
            let metrics = portraitMetrics(for: proxy.size.width)

            ZStack {
                HomeMarqueeStageBackground(glowRadius: 200, glowOpacity: 0.22)

                ClubWallHeadshotFrame(
                    caption: headshotCaption,
                    photoWidth: metrics.photoWidth,
                    photoHeight: metrics.photoHeight,
                    frameWidth: metrics.frameWidth,
                    frameHeight: metrics.frameHeight,
                    captionFontSize: metrics.captionFontSize,
                    captionWidth: metrics.captionWidth,
                    captionHeight: metrics.captionHeight
                ) {
                    artworkImage
                }
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    @ViewBuilder
    private var artworkImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = HomeShowsTonightHeroPresentation.artworkImageURL(for: show).flatMap(URL.normalizedExternalURL) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                fallbackArtwork
            }
        } else {
            fallbackArtwork
        }
    }

    private var fallbackArtwork: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "ticket.fill")
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    private var timeLabel: String {
        ShowFormatting.dateStack(show.date, timezoneID: show.timezone).time
    }

    private var headshotCaption: String {
        HomeShowsTonightHeroPresentation.headshotCaption(for: show)
    }

    private func portraitMetrics(for availableWidth: CGFloat) -> HomeShowsTonightPortraitMetrics {
        let scale = min(1.0, max(0.84, availableWidth / 300))

        return HomeShowsTonightPortraitMetrics(
            photoWidth: 138 * scale,
            photoHeight: 132 * scale,
            frameWidth: 154 * scale,
            frameHeight: 170 * scale,
            captionFontSize: 8.5 * scale,
            captionWidth: 126 * scale,
            captionHeight: 17 * scale
        )
    }

    private var roomLabel: String? {
        // Delegates so the club-name-duplicate suppression in
        // ShowRow.roomLabel applies to the hero venue line too.
        ShowRow.roomLabel(for: show)
    }

    private var venueLine: String {
        let venue = show.clubName ?? "Unknown club"
        guard let roomLabel else { return "At \(venue)" }
        return "At \(venue) • \(roomLabel)"
    }

    private var priceLabel: String? {
        let trimmed = ShowRow.priceLabel(for: show)?.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let trimmed, !trimmed.isEmpty else { return nil }
        return trimmed
    }

    private var accessibilityMetadata: [String] {
        [timeLabel, roomLabel, priceLabel].compactMap { $0 }
    }

}

private struct HomeShowsTonightPortraitMetrics {
    let photoWidth: CGFloat
    let photoHeight: CGFloat
    let frameWidth: CGFloat
    let frameHeight: CGFloat
    let captionFontSize: CGFloat
    let captionWidth: CGFloat
    let captionHeight: CGFloat
}

enum HomeShowsTonightHeroPresentation {
    static func shouldShowFooter(for show: Components.Schemas.Show) -> Bool {
        false
    }

    static func artworkImageURL(for show: Components.Schemas.Show) -> String? {
        if let comedianImageURL = artworkComedian(for: show)?.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty {
            return comedianImageURL
        }

        return show.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
    }

    static func headshotCaption(for show: Components.Schemas.Show) -> String {
        if let comedianName = artworkComedian(for: show)?.name.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty {
            return comedianName
        }

        return ShowTitlePresentation.title(for: show)
    }

    private static func artworkComedian(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        if let showImageComedian = lineupComedianMatchingShowImage(for: show) {
            return showImageComedian
        }

        return ShowRow.artworkComedian(for: show)
    }

    private static func lineupComedianMatchingShowImage(for show: Components.Schemas.Show) -> Components.Schemas.ComedianLineup? {
        let showImageURL = show.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !showImageURL.isEmpty, let lineup = show.lineup else { return nil }

        return lineup
            .map(ShowRow.effectiveComedian)
            .first { comedian in
                comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines) == showImageURL
            }
    }
}

@MainActor
final class HomeShowsTonightModel: ObservableObject {
    static let displayLimit = 5

    static func seeMoreSearchSeed(
        railKind: HomeShowRailKind,
        nearbyPreference: NearbyPreference?
    ) -> SearchRootModel.Seed {
        SearchRootModel.Seed(
            pivot: .shows,
            query: "",
            shortcut: railKind.searchShortcut,
            nearbyPreference: nearbyPreference
        )
    }

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle
    @Published private(set) var cityTitle: String?
    @Published private(set) var feedNearbyPreference: NearbyPreference?

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(
        for zipCode: String?,
        distanceMiles: Int? = nil,
        railKind: HomeShowRailKind? = nil
    ) -> String {
        "\(railKind.map(String.init(describing:)) ?? "showsTonight")|\(HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles))"
    }

    func refresh(
        railKind: HomeShowRailKind = .showsTonight,
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles, railKind: railKind)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, railKind: railKind, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load tonight's shows.",
            rateLimitMessage: "LaughTrack is rate-limiting tonight's shows right now.",
            undocumentedContext: "tonight's shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the home feed. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, railKind: railKind, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind, requestKey: String) {
        cityTitle = Self.locationTitle(city: feed.hero.city, state: feed.hero.state)
        feedNearbyPreference = Self.nearbyPreference(from: feed.hero)
        phase = .success(Self.shows(from: feed, railKind: railKind))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private static func shows(from feed: Components.Schemas.HomeFeed, railKind: HomeShowRailKind) -> [Components.Schemas.Show] {
        let sourceShows: [Components.Schemas.Show]
        switch railKind {
        case .showsTonight:
            sourceShows = feed.showsTonight + feed.hero.shows + feed.trendingThisWeek
        case .thisWeek:
            let tonightIDs = Set((feed.showsTonight + feed.hero.shows).map(\.id))
            sourceShows = (feed.trendingThisWeek + feed.moreNearYou).filter { show in
                !tonightIDs.contains(show.id)
            }
        }

        var seenIDs: Set<Int> = []
        return sourceShows.filter { show in
            !ShowAvailability.isSoldOut(show) && seenIDs.insert(show.id).inserted
        }.prefix(Self.displayLimit).map { $0 }
    }

    private static func locationTitle(city: String?, state: String?) -> String? {
        guard let city, !city.isEmpty else { return nil }
        if let state, !state.isEmpty {
            return "\(city), \(state)"
        }
        return city
    }

    private static func nearbyPreference(from hero: Components.Schemas.HomeFeedHero) -> NearbyPreference? {
        guard let zipCode = hero.zipCode?.filter(\.isNumber), zipCode.count == 5 else {
            return nil
        }

        return NearbyPreference(
            zipCode: zipCode,
            source: .manual,
            distanceMiles: NearbyPreference.defaultDistanceMiles,
            city: hero.city,
            state: hero.state
        )
    }
}

@MainActor
final class HomeFavoriteShowsModel: ObservableObject {
    private static let maxFavoriteQueries = 5
    private static let showsPerFavorite = 3

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func refresh(
        apiClient: Client,
        favoriteComedians: [Components.Schemas.ComedianSearchItem],
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = Self.requestKey(for: favoriteComedians)
        guard !requestKey.isEmpty else {
            loadedRequestKey = nil
            loadedAt = nil
            phase = .idle
            return
        }
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedShows: [Components.Schemas.Show] = await MainPageCache.get(
            .favoriteShows(requestKey: requestKey),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(shows: cachedShows, requestKey: requestKey)
            return
        }

        phase = .loading

        var showsByID: [Int: Components.Schemas.Show] = [:]

        for comedian in favoriteComedians.prefix(Self.maxFavoriteQueries) {
            do {
                let output = try await apiClient.searchShows(
                    .init(
                        query: .init(
                            from: ShowFormatting.apiDate(Date()),
                            page: 0,
                            size: Self.showsPerFavorite,
                            comedian: comedian.name,
                            sort: ShowSortOption.earliest.rawValue
                        ),
                        headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                    )
                )

                guard case .ok(let ok) = output else { continue }
                let response = try ok.body.json
                for show in response.data where Self.show(show, matches: comedian) {
                    showsByID[show.id] = show
                }
            } catch {
                guard !Task.isCancelled else { return }
                continue
            }
        }

        let shows = ShowAvailability.availableShows(Array(showsByID.values)).sorted { $0.date < $1.date }
        await MainPageCache.set(
            shows,
            forKey: .favoriteShows(requestKey: requestKey),
            in: cache,
            ttl: cacheTTL,
            persistentCache: persistentCache
        )
        apply(shows: shows, requestKey: requestKey)
    }

    private func apply(shows: [Components.Schemas.Show], requestKey: String) {
        phase = .success(shows)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func requestKey(for favoriteComedians: [Components.Schemas.ComedianSearchItem]) -> String {
        favoriteComedians.map(\.uuid).joined(separator: "|")
    }

    static func show(
        _ show: Components.Schemas.Show,
        matches favorite: Components.Schemas.ComedianSearchItem
    ) -> Bool {
        guard let lineup = show.lineup, !lineup.isEmpty else { return true }
        return lineup.contains { comedian in
            comedian.uuid == favorite.uuid ||
                comedian.id == favorite.id ||
                comedian.name.localizedCaseInsensitiveCompare(favorite.name) == .orderedSame
        }
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

private struct HomeTrendingComediansRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingComediansModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .posterGrid,
            eyebrow: "Drawing Crowds",
            title: "Popular local comedians",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homeTrendingComediansRail
        ) {
            switch model.phase {
            case .idle, .loading:
                HomeTrendingComediansGridSkeleton(gridColumns: gridColumns)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let items):
                if items.isEmpty {
                    EmptyCard(message: "No trending comedians with photos are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(items, id: \.uuid) { comedian in
                            Button {
                                coordinator.open(.comedian(comedian.id))
                            } label: {
                                HomeTrendingComedianCard(comedian: comedian)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingComedianButton(comedian.id))
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomeTrendingComediansGridSkeleton: View {
    @Environment(\.appTheme) private var theme

    let gridColumns: [GridItem]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceSkeleton

        LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
            ForEach(0..<4, id: \.self) { _ in
                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(laughTrack.colors.heroStart)

                        RoundedRectangle(cornerRadius: 7, style: .continuous)
                            .fill(block)
                            .frame(width: 86, height: 86)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 116)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(height: 14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(theme.spacing.sm)
                .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
                .background(laughTrack.colors.surface)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading trending comedians")
        .accessibilityAddTraits(.isImage)
    }
}

private struct HomeTrendingComedianCard: View {
    let comedian: Components.Schemas.ComedianListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        artwork
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(comedian.name)
    }

    private static let stageHeight: CGFloat = 154

    private var artwork: some View {
        GeometryReader { proxy in
            let metrics = headshotMetrics(for: proxy.size.width)

            ClubWallHeadshotFrame(
                caption: comedian.name,
                photoWidth: metrics.photoWidth,
                photoHeight: metrics.photoHeight,
                frameWidth: metrics.frameWidth,
                frameHeight: metrics.frameHeight,
                captionFontSize: metrics.captionFontSize,
                captionWidth: metrics.captionWidth,
                captionHeight: metrics.captionHeight
            ) {
                posterImage
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
    }

    private func headshotMetrics(for availableWidth: CGFloat) -> HomeShowsTonightPortraitMetrics {
        let scale = min(1.0, max(0.82, availableWidth / 156))

        return HomeShowsTonightPortraitMetrics(
            photoWidth: 124 * scale,
            photoHeight: 119 * scale,
            frameWidth: 144 * scale,
            frameHeight: 154 * scale,
            captionFontSize: 9.0 * scale,
            captionWidth: 116 * scale,
            captionHeight: 16 * scale
        )
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "music.mic")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

}

@MainActor
final class HomeTrendingComediansModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ComedianListItem]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, distanceMiles: Int? = nil) -> String {
        HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles)
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending comedians.",
            rateLimitMessage: "LaughTrack is rate-limiting trending comedians right now.",
            undocumentedContext: "trending comedians",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending comedians service. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(Self.railItems(from: feed.trendingComedians))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func railItems(
        from comedians: [Components.Schemas.ComedianListItem]
    ) -> [Components.Schemas.ComedianListItem] {
        let photoBacked = comedians.filter(hasUsablePhoto)
        guard photoBacked.count >= 10 else {
            return photoBacked
        }

        let noPhoto = comedians.filter { !hasUsablePhoto($0) }
        return photoBacked + noPhoto
    }

    private static func hasUsablePhoto(_ comedian: Components.Schemas.ComedianListItem) -> Bool {
        let rawValue = comedian.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        return URL.normalizedExternalURL(rawValue) != nil
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

private struct HomePopularClubsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomePopularClubsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .posterGrid,
            eyebrow: "Hot Rooms",
            title: "Popular local clubs",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homePopularClubsRail
        ) {
            switch model.phase {
            case .idle, .loading:
                HomePopularClubsGridSkeleton(gridColumns: gridColumns)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let clubs):
                if clubs.isEmpty {
                    EmptyCard(message: "No clubs are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(clubs, id: \.id) { club in
                            Button {
                                coordinator.open(.club(club.id))
                            } label: {
                                HomePopularClubCard(club: club)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomePopularClubsGridSkeleton: View {
    @Environment(\.appTheme) private var theme

    let gridColumns: [GridItem]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceSkeleton

        LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
            ForEach(0..<4, id: \.self) { _ in
                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(laughTrack.colors.heroStart)

                        Circle()
                            .fill(block)
                            .frame(width: 86, height: 86)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 116)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(height: 14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(theme.spacing.sm)
                .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
                .background(laughTrack.colors.surface)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading popular clubs")
        .accessibilityAddTraits(.isImage)
    }
}

private struct HomePopularClubCard: View {
    let club: Components.Schemas.ClubListItem

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            Text(club.name)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(club.name)
    }

    private static let posterSize: CGFloat = 86
    private static let posterFrameInset: CGFloat = 6
    private static let posterCornerRadius: CGFloat = 8
    private static let clubBulbColor = Color(red: 1.0, green: 0.78, blue: 0.24)
    private static let stageHeight: CGFloat = 116

    private var artwork: some View {
        return ZStack {
            HomeMarqueeStageBackground()

            ZStack {
                posterImage
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .clipShape(RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: Self.posterCornerRadius, style: .continuous)
                            .stroke(Color.black.opacity(0.55), lineWidth: 1)
                    )

                HomeBulbFrame(
                    width: Self.posterSize + Self.posterFrameInset,
                    height: Self.posterSize + Self.posterFrameInset,
                    cornerRadius: Self.posterCornerRadius + Self.posterFrameInset / 2,
                    dash: [1.2, 10],
                    bulbColor: Self.clubBulbColor
                )
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens

        if let url = URL.normalizedExternalURL(club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFit()
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .background(laughTrack.colors.surfaceMuted)
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "building.2.fill")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

@MainActor
final class HomePopularClubsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.ClubListItem]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, distanceMiles: Int? = nil) -> String {
        HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles)
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load clubs.",
            rateLimitMessage: "LaughTrack is rate-limiting clubs right now.",
            undocumentedContext: "clubs",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the clubs service. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(feed.popularClubs)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

enum MainPageCache {
    static let defaultTTL: TimeInterval = 60 * 60

    static func get<Value>(
        _ key: LaughTrackCacheKey,
        from cache: DataCache<LaughTrackCacheKey>?,
        persistentCache: PersistentMainPageCache?
    ) async -> Value? {
        if let cached: Value = await cache?.get(forKey: key) {
            return cached
        }

        guard let persistentCache else {
            return nil
        }

        switch key {
        case .homeFeed(let zipCode, let distanceMiles) where Value.self == Components.Schemas.HomeFeed.self:
            guard let cached = await persistentCache.getCachedHomeFeed(
                zipCode: zipCode,
                distanceMiles: distanceMiles
            ) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        case .favoriteShows(let requestKey) where Value.self == [Components.Schemas.Show].self:
            guard let cached = await persistentCache.getCachedFavoriteShows(requestKey: requestKey) else { return nil }
            await hydrateMemoryCache(cached.value, key: key, expiresAt: cached.expiresAt, cache: cache)
            return cached.value as? Value
        default:
            return nil
        }
    }

    static func set(
        _ value: some Sendable,
        forKey key: LaughTrackCacheKey,
        in cache: DataCache<LaughTrackCacheKey>?,
        ttl: TimeInterval = defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        await cache?.set(value, forKey: key, ttl: ttl)

        switch key {
        case .homeFeed(let zipCode, let distanceMiles):
            guard let homeFeed = value as? Components.Schemas.HomeFeed else { return }
            await persistentCache?.setHomeFeed(
                homeFeed,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                ttl: ttl
            )
        case .favoriteShows(let requestKey):
            guard let shows = value as? [Components.Schemas.Show] else { return }
            await persistentCache?.setFavoriteShows(shows, requestKey: requestKey, ttl: ttl)
        default:
            return
        }
    }

    private static func hydrateMemoryCache(
        _ value: some Sendable,
        key: LaughTrackCacheKey,
        expiresAt: Date,
        cache: DataCache<LaughTrackCacheKey>?
    ) async {
        await cache?.set(value, forKey: key, ttl: max(0, expiresAt.timeIntervalSinceNow))
    }
}

// Internal (not private) so tests can inject a fresh instance per test:
// the process-wide .shared instance coalesces by zip|distance key only, so
// concurrently-running test suites that refresh with the same key would
// otherwise receive each other's mock-transport feeds (TASK-2756).
actor HomeFeedRequestCoalescer {
    static let shared = HomeFeedRequestCoalescer()

    private var inFlight: [String: Task<Result<Components.Schemas.HomeFeed, LoadFailure>, Never>] = [:]

    func load(
        requestKey: String,
        operation: @escaping @Sendable () async -> Result<Components.Schemas.HomeFeed, LoadFailure>
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        if let task = inFlight[requestKey] {
            return await task.value
        }

        let task = Task {
            await operation()
        }
        inFlight[requestKey] = task
        let result = await task.value
        inFlight[requestKey] = nil
        return result
    }
}

private enum HomeFeedRequest {
    static func requestKey(zipCode: String?, distanceMiles: Int?) -> String {
        "\(zipCode ?? "")|\(distanceMiles.map(String.init) ?? "")"
    }

    static func load(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        await coalescer.load(requestKey: requestKey(zipCode: zipCode, distanceMiles: distanceMiles)) {
            await fetch(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                cacheTTL: cacheTTL,
                badParamsMessage: badParamsMessage,
                rateLimitMessage: rateLimitMessage,
                undocumentedContext: undocumentedContext,
                networkContext: networkContext,
                networkMessage: networkMessage,
                persistentCache: persistentCache
            )
        }
    }

    private static func fetch(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval,
        badParamsMessage: String,
        rateLimitMessage: String,
        undocumentedContext: String,
        networkContext: String,
        networkMessage: String,
        persistentCache: PersistentMainPageCache?
    ) async -> Result<Components.Schemas.HomeFeed, LoadFailure> {
        do {
            let output = try await apiClient.getHomeFeed(
                .init(
                    query: .init(zip: zipCode, distance: zipCode == nil ? nil : distanceMiles),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                await MainPageCache.set(
                    response.data,
                    forKey: .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
                    in: cache,
                    ttl: cacheTTL,
                    persistentCache: persistentCache
                )
                return .success(response.data)
            case .badRequest(let badRequest):
                return .failure(
                    .badParams((try? badRequest.body.json.error) ?? badParamsMessage)
                )
            case .tooManyRequests(let tooManyRequests):
                return .failure(
                    .rateLimited(retryAfter: nil, message: (try? tooManyRequests.body.json.error) ?? rateLimitMessage)
                )
            case .internalServerError(let serverError):
                return .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: undocumentedContext))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: networkContext,
                networkMessage: networkMessage
            ))
        }
    }
}

struct HomeTrendingPodcastsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @StateObject private var model = HomeTrendingPodcastsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        HomeDiscoverRailCard(
            variant: .listeningRoom,
            eyebrow: "Funny listening",
            title: "Popular comedy podcasts",
            subtitle: nil,
            accessibilityIdentifier: LaughTrackViewTestID.homeTrendingPodcastsRail
        ) {
            switch model.phase {
            case .idle, .loading:
                HomeTrendingPodcastsGridSkeleton(gridColumns: gridColumns)
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: {
                        await model.refresh(
                            apiClient: apiClient,
                            zipCode: zipCode,
                            distanceMiles: distanceMiles,
                            cache: cache,
                            persistentCache: persistentCache
                        )
                    },
                    signIn: { coordinator.push(.profile) }
                )
            case .success(let items):
                if items.isEmpty {
                    EmptyCard(message: "No trending podcasts are available right now.")
                } else {
                    LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
                        ForEach(items, id: \.id) { podcast in
                            Button {
                                coordinator.open(.podcast(podcast.id))
                            } label: {
                                HomeTrendingPodcastCard(podcast: podcast)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.homeTrendingPodcastButton(podcast.id))
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }

    private var gridColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: theme.spacing.sm),
            GridItem(.flexible(), spacing: theme.spacing.sm),
        ]
    }
}

private struct HomeTrendingPodcastsGridSkeleton: View {
    @Environment(\.appTheme) private var theme

    let gridColumns: [GridItem]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let block = laughTrack.colors.surfaceSkeleton

        LazyVGrid(columns: gridColumns, spacing: theme.spacing.sm) {
            ForEach(0..<4, id: \.self) { _ in
                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(laughTrack.colors.heroStart)

                        RoundedRectangle(cornerRadius: 7, style: .continuous)
                            .fill(block)
                            .frame(width: 86, height: 86)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 116)

                    RoundedRectangle(cornerRadius: 4)
                        .fill(block)
                        .frame(height: 14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(theme.spacing.sm)
                .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
                .background(laughTrack.colors.surface)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
        }
        .detailSkeletonShimmer()
        .accessibilityLabel("Loading trending podcasts")
        .accessibilityAddTraits(.isImage)
    }
}

private struct HomeTrendingPodcastCard: View {
    let podcast: Components.Schemas.HomeFeedPodcast

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            artwork

            Text(podcast.title)
                .font(laughTrack.typography.body.weight(.semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(theme.spacing.sm)
        .frame(maxWidth: .infinity, minHeight: 172, alignment: .topLeading)
        .background(laughTrack.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(podcast.title)
    }

    private static let coverSize: CGFloat = 88
    private static let coverCornerRadius: CGFloat = 8
    private static let stageHeight: CGFloat = 116

    private var artwork: some View {
        return ZStack {
            HomeMarqueeStageBackground(glowOpacity: 0.16)

            VStack(spacing: 7) {
                podcastCover
                waveformStrip
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var podcastCover: some View {
        posterImage
            .frame(width: Self.coverSize, height: Self.coverSize)
            .clipShape(RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous)
                    .stroke(Color.black.opacity(0.55), lineWidth: 1)
            )
            .overlay(alignment: .topTrailing) {
                rssBadge
                    .padding(5)
            }
            .shadow(color: .black.opacity(0.42), radius: 8, y: 5)
    }

    private var rssBadge: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            Circle()
                .fill(Color.black.opacity(0.72))

            Image(systemName: "dot.radiowaves.left.and.right")
                .font(.system(size: 11, weight: .heavy))
                .foregroundStyle(laughTrack.colors.accentStrong)
        }
        .frame(width: 24, height: 24)
        .overlay(
            Circle()
                .stroke(laughTrack.colors.accentStrong.opacity(0.92), lineWidth: 1)
        )
        .shadow(color: laughTrack.colors.accentStrong.opacity(0.35), radius: 6)
    }

    private var waveformStrip: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(spacing: 3) {
            Image(systemName: "waveform")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(laughTrack.colors.accentStrong.opacity(0.92))

            HStack(alignment: .center, spacing: 2) {
                ForEach(0..<9, id: \.self) { index in
                    Capsule(style: .continuous)
                        .fill(laughTrack.colors.accentStrong.opacity(0.92))
                        .frame(width: 2, height: CGFloat([7, 13, 9, 18, 11, 15, 8, 12, 6][index]))
                }
            }
        }
        .padding(.horizontal, 8)
        .frame(height: 18)
        .background(Color.black.opacity(0.36), in: Capsule(style: .continuous))
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = podcast.imageUrl?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let raw = trimmed, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: "headphones")
                    .font(.system(size: theme.iconSizes.lg, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

@MainActor
final class HomeTrendingPodcastsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.HomeFeedPodcast]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, distanceMiles: Int? = nil) -> String {
        HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles)
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles)
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load trending podcasts.",
            rateLimitMessage: "LaughTrack is rate-limiting trending podcasts right now.",
            undocumentedContext: "trending podcasts",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the trending podcasts service. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(feed.trendingPodcasts)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
