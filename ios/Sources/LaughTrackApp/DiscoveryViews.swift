import Combine
import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

private enum DiscoverySection: String, CaseIterable, Identifiable {
    case shows
    case comedians
    case clubs

    var id: String { rawValue }

    var title: String {
        switch self {
        case .shows: return "Shows"
        case .comedians: return "Comedians"
        case .clubs: return "Clubs"
        }
    }

    var subtitle: String {
        switch self {
        case .shows: return "Upcoming dates and ticket links."
        case .comedians: return "Search talent and save favorites."
        case .clubs: return "Browse rooms and venue links."
        }
    }
}

struct DiscoveryHubView: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @State private var selection: DiscoverySection = .shows
    @StateObject private var showsModel: ShowsDiscoveryModel
    @StateObject private var comediansModel = ComediansDiscoveryModel()
    @StateObject private var clubsModel = ClubsDiscoveryModel()

    init(
        apiClient: Client,
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        _showsModel = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackCard(tone: .accent) {
                VStack(alignment: .leading, spacing: theme.spacing.lg) {
                    LaughTrackSectionHeader(
                        eyebrow: "Browse",
                        title: selection.title,
                        subtitle: selection.subtitle
                    )

                    Picker("Browse", selection: $selection) {
                        ForEach(DiscoverySection.allCases) { section in
                            Text(section.title).tag(section)
                        }
                    }
                    .pickerStyle(.segmented)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            ForEach(DiscoverySection.allCases) { section in
                                LaughTrackBadge(
                                    section.title,
                                    systemImage: badgeIcon(for: section),
                                    tone: selection == section ? .highlight : .neutral
                                )
                            }
                        }
                    }
                }
            }

            Group {
                switch selection {
                case .shows:
                    ShowsDiscoveryView(apiClient: apiClient, model: showsModel)
                case .comedians:
                    ComediansDiscoveryView(apiClient: apiClient, model: comediansModel)
                case .clubs:
                    ClubsDiscoveryView(apiClient: apiClient, model: clubsModel)
                }
            }
        }
    }

    private func badgeIcon(for section: DiscoverySection) -> String {
        switch section {
        case .shows:
            return "ticket.fill"
        case .comedians:
            return "music.mic"
        case .clubs:
            return "building.2.fill"
        }
    }
}

struct HomeNearbyPage {
    let items: [Components.Schemas.Show]
    let total: Int
    let zipCapTriggered: Bool
}

@MainActor
final class HomeNearbyDiscoveryModel: ObservableObject {
    @Published var zipCodeDraft = ""
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var phase: LoadPhase<HomeNearbyPage> = .idle
    @Published private(set) var zipValidationMessage: String?
    @Published private(set) var locationMessage: String?
    @Published private(set) var isEditingZip = false
    @Published private(set) var isResolvingLocation = false
    @Published private(set) var isPromptDismissed: Bool

    private let nearbyPreferenceStore: NearbyPreferenceStore
    private let appStateStorage: AppStateStorageProtocol
    private let nearbyLocationController: NearbyLocationController
    private var preferenceCancellable: AnyCancellable?
    private var locationStatusCancellable: AnyCancellable?
    private var locationLoadingCancellable: AnyCancellable?
    private var loadedPreference: NearbyPreference?

    init(
        nearbyPreferenceStore: NearbyPreferenceStore,
        nearbyLocationController: NearbyLocationController,
        appStateStorage: AppStateStorageProtocol = AppStateStorage()
    ) {
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.appStateStorage = appStateStorage
        self.nearbyLocationController = nearbyLocationController
        self.isPromptDismissed = appStateStorage.getValue(
            forKey: StorageKey.promptDismissed,
            as: Bool.self
        ) ?? false
        self.activeNearbyPreference = nearbyPreferenceStore.preference
        self.zipCodeDraft = nearbyPreferenceStore.preference?.zipCode ?? ""

        preferenceCancellable = nearbyPreferenceStore.$preference
            .sink { [weak self] preference in
                self?.applyNearbyPreference(preference)
            }
        locationStatusCancellable = nearbyLocationController.$statusMessage
            .sink { [weak self] message in
                self?.locationMessage = message
            }
        locationLoadingCancellable = nearbyLocationController.$isResolvingCurrentLocation
            .sink { [weak self] isResolving in
                self?.isResolvingLocation = isResolving
            }
    }

    var requestKey: NearbyPreference? {
        activeNearbyPreference
    }

    var shouldShowPrompt: Bool {
        activeNearbyPreference == nil && !isPromptDismissed
    }

    func refresh(apiClient: Client) async {
        guard let preference = activeNearbyPreference else {
            loadedPreference = nil
            phase = .idle
            return
        }

        if loadedPreference == preference, case .success = phase {
            return
        }

        phase = .loading

        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: preference.zipCode,
                        from: nil,
                        to: nil,
                        page: 0,
                        size: 4,
                        comedian: nil,
                        club: nil,
                        distance: preference.distanceMiles,
                        sort: ShowSortOption.earliest.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                phase = .success(
                    .init(
                        items: response.data,
                        total: response.total,
                        zipCapTriggered: response.zipCapTriggered
                    )
                )
                loadedPreference = preference
            case .badRequest(let badRequest):
                phase = .failure(
                    .badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those nearby filters.")
                )
            case .internalServerError(let serverError):
                phase = .failure(
                    .serverError(status: 500, message: (try? serverError.body.json.error))
                )
            case .undocumented(let status, _):
                phase = .failure(classifyUndocumented(status: status, context: "nearby shows"))
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .failure(
                .network("LaughTrack couldn't reach the nearby shows service. Check your connection and try again.")
            )
        }
    }

    func presentZipEntry() {
        setPromptDismissed(false)
        isEditingZip = true
        zipValidationMessage = nil
        locationMessage = nil
    }

    func dismissPrompt() {
        isEditingZip = false
        locationMessage = nil
        setPromptDismissed(true)
    }

    func clearNearby() {
        isEditingZip = false
        zipCodeDraft = ""
        loadedPreference = nil
        setPromptDismissed(false)
        nearbyLocationController.clear()
    }

    func applyManualZip() -> Bool {
        guard let preference = nearbyPreferenceStore.setManualZip(zipCodeDraft) else {
            zipValidationMessage = "Enter a valid 5-digit ZIP code to search nearby shows."
            return false
        }

        zipCodeDraft = preference.zipCode
        zipValidationMessage = nil
        locationMessage = nil
        isEditingZip = false
        return true
    }

    func useCurrentLocation() async {
        zipValidationMessage = nil
        let distanceMiles = activeNearbyPreference?.distanceMiles
            ?? NearbyPreference.defaultDistanceMiles
        let succeeded = await nearbyLocationController.useCurrentLocation(
            distanceMiles: distanceMiles
        )
        if succeeded {
            isEditingZip = false
        }
    }

    private func applyNearbyPreference(_ preference: NearbyPreference?) {
        activeNearbyPreference = preference
        zipValidationMessage = nil

        if let preference {
            zipCodeDraft = preference.zipCode
            loadedPreference = nil
            if isPromptDismissed {
                setPromptDismissed(false)
            }
        } else {
            loadedPreference = nil
            phase = .idle
            if !isEditingZip {
                zipCodeDraft = ""
            }
        }
    }

    private func setPromptDismissed(_ dismissed: Bool) {
        isPromptDismissed = dismissed
        appStateStorage.setValue(dismissed, forKey: StorageKey.promptDismissed)
    }

    private enum StorageKey {
        static let promptDismissed = "laughtrack.discovery.home-nearby-prompt-dismissed"
    }
}

struct HomeNearbyDiscoverySection: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @StateObject private var model: HomeNearbyDiscoveryModel

    init(
        apiClient: Client,
        nearbyPreferenceStore: NearbyPreferenceStore,
        nearbyLocationController: NearbyLocationController
    ) {
        self.apiClient = apiClient
        _model = StateObject(
            wrappedValue: HomeNearbyDiscoveryModel(
                nearbyPreferenceStore: nearbyPreferenceStore,
                nearbyLocationController: nearbyLocationController
            )
        )
    }

    var body: some View {
        DiscoveryCard(title: "Nearby tonight") {
            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                if model.shouldShowPrompt {
                    promptContent
                } else if let preference = model.activeNearbyPreference {
                    nearbyResultsContent(preference: preference)
                } else {
                    collapsedContent
                }
            }
        }
        .task(id: model.requestKey) {
            await model.refresh(apiClient: apiClient)
        }
    }

    @ViewBuilder
    private var promptContent: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Start with the room around you",
                subtitle: "Use your current location or drop in a ZIP code. LaughTrack keeps the rest of home available even if you skip this for now."
            )

            HStack(spacing: theme.spacing.sm) {
                LaughTrackBadge("Optional", systemImage: "hand.raised", tone: .neutral)
                LaughTrackBadge("No lock-in", systemImage: "location.slash", tone: .highlight)
            }

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton(
                    model.isResolvingLocation ? "Finding your ZIP…" : "Use current location",
                    systemImage: "location.fill"
                ) {
                    Task {
                        await model.useCurrentLocation()
                    }
                }
                .disabled(model.isResolvingLocation)

                LaughTrackButton("Enter a ZIP instead", systemImage: "mappin.and.ellipse", tone: .secondary) {
                    model.presentZipEntry()
                }

                LaughTrackButton("Not now", systemImage: "arrow.right", tone: .tertiary) {
                    model.dismissPrompt()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages
        }
    }

    @ViewBuilder
    private func nearbyResultsContent(preference: NearbyPreference) -> some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Shows around ZIP \(preference.zipCode)",
                subtitle: preference.source == .manual
                    ? "Using your saved ZIP and radius preference from home."
                    : "Using the ZIP closest to your current location."
            )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    LaughTrackBadge("ZIP \(preference.zipCode)", systemImage: "mappin.and.ellipse", tone: .neutral)
                    LaughTrackBadge("Within \(preference.distanceMiles) mi", systemImage: "location.fill", tone: .highlight)
                    LaughTrackBadge(
                        preference.source == .manual ? "Saved manually" : "Current location",
                        systemImage: preference.source == .manual ? "slider.horizontal.3" : "location.north.line",
                        tone: .accent
                    )
                }
            }

            HStack(spacing: theme.spacing.sm) {
                LaughTrackButton("Change ZIP", systemImage: "pencil", tone: .secondary, fullWidth: false) {
                    model.presentZipEntry()
                }
                LaughTrackButton("Clear nearby", systemImage: "location.slash", tone: .tertiary, fullWidth: false) {
                    model.clearNearby()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages

            switch model.phase {
            case .idle, .loading:
                LoadingCard()
            case .failure(let failure):
                FailureCard(
                    failure: failure,
                    retry: { await model.refresh(apiClient: apiClient) },
                    signIn: { coordinator.push(.settings) }
                )
            case .success(let result):
                if result.items.isEmpty {
                    EmptyCard(message: "No nearby shows matched this ZIP yet. Broaden the radius below or clear nearby filters.")
                } else {
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        SearchResultsSummary(count: result.items.count, total: result.total)

                        if result.zipCapTriggered {
                            InlineStatusMessage(message: "That ZIP was broadened by the server because it covered too many locations. Tighten the ZIP or clear nearby filters.")
                        }

                        ForEach(Array(result.items.prefix(3)), id: \.id) { show in
                            Button {
                                coordinator.open(.show(show.id))
                            } label: {
                                ShowRow(show: show)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var collapsedContent: some View {
        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            LaughTrackSectionHeader(
                eyebrow: "Nearby",
                title: "Nearby browsing is paused",
                subtitle: "You can keep browsing nationally below, or turn nearby back on whenever you want."
            )

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton(
                    model.isResolvingLocation ? "Finding your ZIP…" : "Use current location",
                    systemImage: "location.fill"
                ) {
                    Task {
                        await model.useCurrentLocation()
                    }
                }
                .disabled(model.isResolvingLocation)

                LaughTrackButton("Enter a ZIP instead", systemImage: "mappin.and.ellipse", tone: .secondary) {
                    model.presentZipEntry()
                }
            }

            if model.isEditingZip {
                homeZipField
            }

            statusMessages
        }
    }

    private var homeZipField: some View {
        LaughTrackLabeledField(title: "ZIP", detail: "5 digits") {
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                TextField("10012", text: $model.zipCodeDraft)
                    .modifier(SearchFieldInputBehavior())
                    #if os(iOS)
                    .keyboardType(UIKeyboardType.numberPad)
                    #endif

                LaughTrackButton("Use this ZIP", systemImage: "checkmark", tone: .secondary, fullWidth: false) {
                    _ = model.applyManualZip()
                }
            }
        }
    }

    @ViewBuilder
    private var statusMessages: some View {
        if let zipValidationMessage = model.zipValidationMessage {
            InlineStatusMessage(message: zipValidationMessage)
        }

        if let locationMessage = model.locationMessage {
            InlineStatusMessage(message: locationMessage)
        }
    }
}

struct ShowRow: View {
    let show: Components.Schemas.Show

    var body: some View {
        LaughTrackResultRow(
            title: show.name ?? "Untitled show",
            subtitle: show.clubName ?? "Unknown club",
            metadata: [
                ShowFormatting.listDate(show.date),
                ShowFormatting.distance(show.distanceMiles),
                show.soldOut == true ? "Sold out" : nil,
            ].compactMap { $0 },
            systemImage: "ticket.fill",
            imageURL: show.imageUrl
        )
    }
}

struct FavoriteButton: View {
    @Environment(\.appTheme) private var theme

    let isFavorite: Bool
    let isPending: Bool
    let action: () async -> Void

    var body: some View {
        Button {
            Task {
                await action()
            }
        } label: {
            if isPending {
                ProgressView()
                    .progressViewStyle(.circular)
                    .frame(width: 28, height: 28)
            } else {
                Image(systemName: isFavorite ? "heart.fill" : "heart")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(isFavorite ? theme.laughTrackTokens.colors.accent : theme.laughTrackTokens.colors.textSecondary)
                    .frame(width: 28, height: 28)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(isFavorite ? "Remove favorite" : "Add favorite")
    }
}

struct SearchResultsSummary: View {
    @Environment(\.appTheme) private var theme

    let count: Int
    let total: Int

    var body: some View {
        LaughTrackContextRow(leading: "Showing \(count) of \(total)")
    }
}

struct InlineStatusMessage: View {
    @Environment(\.appTheme) private var theme

    let message: String

    var body: some View {
        LaughTrackCard(tone: .muted, density: .compact) {
            HStack(alignment: .top, spacing: theme.spacing.sm) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(theme.laughTrackTokens.colors.accent)
                Text(message)
                    .font(theme.laughTrackTokens.typography.metadata)
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

struct LoadMoreButton: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let isLoading: Bool
    let action: () async -> Void

    var body: some View {
        LaughTrackButton(
            isLoading ? "Loading…" : title,
            systemImage: isLoading ? nil : "arrow.down.circle",
            tone: .primary,
            density: .compact
        ) {
            Task {
                await action()
            }
        }
        .disabled(isLoading)
        .overlay(alignment: .trailing) {
            if isLoading {
                ProgressView()
                    .progressViewStyle(.circular)
                    .padding(.trailing, theme.spacing.lg)
            }
        }
    }
}

struct DiscoveryCard<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                LaughTrackSectionHeader(eyebrow: "Browse", title: title)
                content
            }
        }
    }
}

struct LoadingCard: View {
    let title: String

    init(title: String = "Loading") {
        self.title = title
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .loading,
            title: title,
            message: "LaughTrack is fetching the latest data for this view."
        )
    }
}

struct EmptyCard: View {
    let title: String
    let message: String

    init(title: String = "Nothing here yet", message: String) {
        self.title = title
        self.message = message
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .empty,
            title: title,
            message: message
        )
    }
}

struct FailureCard: View {
    let failure: LoadFailure
    let retry: () async -> Void
    let signIn: () -> Void

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .error,
            title: failure.defaultTitle,
            message: failure.message,
            actionTitle: actionTitle
        ) {
            performAction()
        }
    }

    private var actionTitle: String {
        switch failure.recoveryAction {
        case .signIn:
            return "Sign in"
        case .retry:
            return "Try again"
        }
    }

    private func performAction() {
        switch failure.recoveryAction {
        case .signIn:
            signIn()
        case .retry:
            Task { await retry() }
        }
    }
}

struct SearchFieldInputBehavior: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
        #else
        content
        #endif
    }
}

enum ShowFormatting {
    private static let apiFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static let listFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter
    }()

    static func listDate(_ date: Date) -> String {
        listFormatter.string(from: date)
    }

    static func apiDate(_ date: Date) -> String {
        apiFormatter.string(from: date)
    }

    static func detailDate(_ date: Date, timezoneID: String?) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .full
        formatter.timeStyle = .short
        if let timezoneID, let timezone = TimeZone(identifier: timezoneID) {
            formatter.timeZone = timezone
        }
        return formatter.string(from: date)
    }

    static func distance(_ miles: Double?) -> String? {
        guard let miles else { return nil }
        return String(format: "%.1f miles away", miles)
    }
}

enum FavoriteFeedback {
    static func message(for name: String, isFavorite: Bool) -> String {
        isFavorite ? "Saved \(name) to favorites." : "Removed \(name) from favorites."
    }
}

enum DemoFixtures {
    static let primarySocial = Components.Schemas.SocialData(
        id: 500,
        instagramAccount: "marknormand",
        instagramFollowers: 370000,
        tiktokAccount: "marknormand",
        tiktokFollowers: 210000,
        youtubeAccount: "marknormand",
        youtubeFollowers: 128000,
        website: "marknormandcomedy.com",
        popularity: 0.93,
        linktree: "https://linktr.ee/marknormand"
    )

    static let altSocial = Components.Schemas.SocialData(
        id: 501,
        instagramAccount: "atsukocomedy",
        instagramFollowers: 248000,
        tiktokAccount: "atsukocomedy",
        tiktokFollowers: 420000,
        youtubeAccount: nil,
        youtubeFollowers: nil,
        website: "https://www.atsukocomedy.com",
        popularity: 0.88,
        linktree: nil
    )

    static let thirdSocial = Components.Schemas.SocialData(
        id: 502,
        instagramAccount: "sammorril",
        instagramFollowers: 199000,
        tiktokAccount: nil,
        tiktokFollowers: nil,
        youtubeAccount: "sammorril",
        youtubeFollowers: 92000,
        website: "https://www.sammorril.com",
        popularity: 0.84,
        linktree: nil
    )

    static let comediansIndex: [Components.Schemas.ComedianSearchItem] = [
        .init(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial, showCount: 12, isFavorite: false),
        .init(id: 102, uuid: "demo-comedian-102", name: "Atsuko Okatsuka", imageUrl: altImage, socialData: altSocial, showCount: 8, isFavorite: true),
        .init(id: 103, uuid: "demo-comedian-103", name: "Sam Morril", imageUrl: thirdImage, socialData: thirdSocial, showCount: 6, isFavorite: false)
    ]

    static let clubIndex: [Components.Schemas.ClubSearchItem] = [
        .init(id: 201, address: "117 MacDougal St, New York, NY", name: "Comedy Cellar", zipCode: "10012", imageUrl: clubImage, showCount: 14, isFavorite: nil, city: "New York", state: "NY", phoneNumber: "(212) 254-3480", socialData: nil, activeComedianCount: 62, distanceMiles: nil),
        .init(id: 202, address: "116 E 16th St, New York, NY", name: "The Stand", zipCode: "10003", imageUrl: clubAltImage, showCount: 11, isFavorite: nil, city: "New York", state: "NY", phoneNumber: "(212) 677-2600", socialData: nil, activeComedianCount: 48, distanceMiles: nil)
    ]

    static let shows: [Components.Schemas.Show] = [
        .init(
            id: 301,
            clubName: "Comedy Cellar",
            date: Date().addingTimeInterval(60 * 60 * 24),
            tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/demo/tickets/301", soldOut: false, _type: "General admission")],
            name: "Mark Normand and Friends",
            socialData: nil,
            lineup: lineupForPrimaryShow,
            description: "A demo lineup used for design-system previews.",
            address: "117 MacDougal St, New York, NY",
            room: "Main Room",
            imageUrl: stageImage,
            soldOut: false,
            distanceMiles: 2.1
        ),
        .init(
            id: 302,
            clubName: "The Stand",
            date: Date().addingTimeInterval(60 * 60 * 28),
            tickets: [.init(price: 24, purchaseUrl: nil, soldOut: false, _type: "Preferred seating")],
            name: "Atsuko Late Set",
            socialData: nil,
            lineup: [lineupForPrimaryShow[1]],
            description: "Demo fallback detail for a club-forward lineup.",
            address: "116 E 16th St, New York, NY",
            room: "Upstairs",
            imageUrl: altImage,
            soldOut: false,
            distanceMiles: 3.4
        )
    ]

    static let primaryShowDetail = showDetailResponse(id: 301) ?? Components.Schemas.ShowDetailResponse(data: showDetailData(for: 301), relatedShows: shows)
    static let primaryComedian = comedianDetail(id: 101) ?? Components.Schemas.ComedianDetail(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial)
    static let primaryClub = clubDetail(id: 201) ?? Components.Schemas.ClubDetail(id: 201, name: "Comedy Cellar", imageUrl: clubImage, website: "https://www.comedycellar.com", address: "117 MacDougal St, New York, NY", zipCode: "10012", phoneNumber: "(212) 254-3480")

    static func comedians(matching query: String) -> [Components.Schemas.ComedianSearchItem] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return comediansIndex }
        return comediansIndex.filter { $0.name.localizedCaseInsensitiveContains(trimmed) }
    }

    static func clubs(matching query: String) -> [Components.Schemas.ClubSearchItem] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return clubIndex }
        return clubIndex.filter { ($0.name ?? "").localizedCaseInsensitiveContains(trimmed) }
    }

    static func comedianDetail(id: Int) -> Components.Schemas.ComedianDetail? {
        switch id {
        case 101:
            return .init(id: 101, uuid: "demo-comedian-101", name: "Mark Normand", imageUrl: heroImage, socialData: primarySocial)
        case 102:
            return .init(id: 102, uuid: "demo-comedian-102", name: "Atsuko Okatsuka", imageUrl: altImage, socialData: altSocial)
        case 103:
            return .init(id: 103, uuid: "demo-comedian-103", name: "Sam Morril", imageUrl: thirdImage, socialData: thirdSocial)
        default:
            return nil
        }
    }

    static func clubDetail(id: Int) -> Components.Schemas.ClubDetail? {
        switch id {
        case 201:
            return .init(id: 201, name: "Comedy Cellar", imageUrl: clubImage, website: "https://www.comedycellar.com", address: "117 MacDougal St, New York, NY", zipCode: "10012", phoneNumber: "(212) 254-3480")
        case 202:
            return .init(id: 202, name: "The Stand", imageUrl: clubAltImage, website: "https://thestandnyc.com", address: "116 E 16th St, New York, NY", zipCode: "10003", phoneNumber: "(212) 677-2600")
        default:
            return nil
        }
    }

    static func showDetailResponse(id: Int) -> Components.Schemas.ShowDetailResponse? {
        switch id {
        case 301:
            return .init(data: showDetailData(for: 301), relatedShows: [shows[1]])
        case 302:
            return .init(data: showDetailData(for: 302), relatedShows: [shows[0]])
        default:
            return nil
        }
    }

    private static func showDetailData(for id: Int) -> Components.Schemas.ShowDetail {
        switch id {
        case 301:
            return .init(
                id: 301,
                clubName: "Comedy Cellar",
                date: Date().addingTimeInterval(60 * 60 * 24),
                tickets: [.init(price: 30, purchaseUrl: "https://laughtrack.app/demo/tickets/301", soldOut: false, _type: "General admission")],
                name: "Mark Normand and Friends",
                socialData: nil,
                lineup: lineupForPrimaryShow,
                description: "A native detail presentation for the generated show contract, including CTA fallback and lineup favorites.",
                address: "117 MacDougal St, New York, NY",
                room: "Main Room",
                imageUrl: stageImage,
                soldOut: false,
                distanceMiles: 2.1,
                timezone: "America/New_York",
                showPageUrl: "https://laughtrack.app/demo/shows/301",
                club: .init(id: 201, name: "Comedy Cellar", address: "117 MacDougal St, New York, NY", imageUrl: clubImage, timezone: "America/New_York"),
                cta: .init(url: "https://laughtrack.app/demo/tickets/301", label: "Buy tickets", isSoldOut: false)
            )
        default:
            return .init(
                id: 302,
                clubName: "The Stand",
                date: Date().addingTimeInterval(60 * 60 * 28),
                tickets: [.init(price: 24, purchaseUrl: nil, soldOut: false, _type: "Preferred seating")],
                name: "Atsuko Late Set",
                socialData: nil,
                lineup: [lineupForPrimaryShow[1]],
                description: "The CTA falls back to the show page when a direct purchase link is missing.",
                address: "116 E 16th St, New York, NY",
                room: "Upstairs",
                imageUrl: altImage,
                soldOut: false,
                distanceMiles: 3.4,
                timezone: "America/New_York",
                showPageUrl: "https://laughtrack.app/demo/shows/302",
                club: .init(id: 202, name: "The Stand", address: "116 E 16th St, New York, NY", imageUrl: clubAltImage, timezone: "America/New_York"),
                cta: .init(url: nil, label: "Open show page", isSoldOut: false)
            )
        }
    }

    private static let lineupForPrimaryShow: [Components.Schemas.ComedianLineup] = [
        .init(name: "Mark Normand", imageUrl: heroImage, uuid: "demo-comedian-101", id: 101, userId: nil, socialData: primarySocial, isFavorite: false, showCount: 12),
        .init(name: "Atsuko Okatsuka", imageUrl: altImage, uuid: "demo-comedian-102", id: 102, userId: nil, socialData: altSocial, isFavorite: true, showCount: 8),
        .init(name: "Sam Morril", imageUrl: thirdImage, uuid: "demo-comedian-103", id: 103, userId: nil, socialData: thirdSocial, isFavorite: false, showCount: 6)
    ]

    private static let heroImage = "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=1200&q=80"
    private static let altImage = "https://images.unsplash.com/photo-1509824227185-9c5a01ceba0d?auto=format&fit=crop&w=1200&q=80"
    private static let thirdImage = "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1200&q=80"
    private static let stageImage = "https://images.unsplash.com/photo-1503095396549-807759245b35?auto=format&fit=crop&w=1200&q=80"
    private static let clubImage = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80"
    private static let clubAltImage = "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?auto=format&fit=crop&w=1200&q=80"
}

enum DemoContent {
    static let primaryShowDetail = DemoFixtures.primaryShowDetail
    static let primaryComedian = DemoFixtures.primaryComedian

    static func showDetailResponse(id: Int) -> Components.Schemas.ShowDetailResponse? {
        DemoFixtures.showDetailResponse(id: id)
    }

    static func comedianDetail(id: Int) -> Components.Schemas.ComedianDetail? {
        DemoFixtures.comedianDetail(id: id)
    }
}

extension String {
    var nonEmpty: String? {
        isEmpty ? nil : self
    }

    func socialURL(host: String) -> URL? {
        guard !isEmpty else { return nil }
        return URL(string: "https://\(host)\(self.hasPrefix("@") ? String(self.dropFirst()) : self)")
    }
}

extension URL {
    static func normalizedExternalURL(_ rawValue: String?) -> URL? {
        guard let rawValue, !rawValue.isEmpty else { return nil }
        if let direct = URL(string: rawValue), direct.scheme != nil {
            return direct
        }
        return URL(string: "https://\(rawValue)")
    }

    static func phoneURL(_ rawValue: String?) -> URL? {
        guard let rawValue, !rawValue.isEmpty else { return nil }
        let digits = rawValue.filter(\.isNumber)
        guard !digits.isEmpty else { return nil }
        return URL(string: "tel://\(digits)")
    }

    static func mapsURL(for address: String) -> URL? {
        guard
            !address.isEmpty,
            let encodedAddress = address.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed)
        else { return nil }
        return URL(string: "http://maps.apple.com/?q=\(encodedAddress)")
    }
}
