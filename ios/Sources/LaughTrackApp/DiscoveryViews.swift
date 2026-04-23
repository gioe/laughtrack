import Combine
import CoreLocation
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
        case .shows: return "Upcoming dates and live ticket CTAs."
        case .comedians: return "Search talent and save favorites."
        case .clubs: return "Browse rooms and venue links."
        }
    }
}

@MainActor
final class ComedianFavoriteStore: ObservableObject {
    enum ToggleResult {
        case updated(Bool)
        case signInRequired(String)
        case failure(String)
    }

    enum SavedFavoritesPhase: Equatable {
        case idle
        case loading
        case loaded
        case empty
        case failure(String)
    }

    @Published private var values: [String: Bool] = [:]
    @Published private var pending: Set<String> = []
    @Published private(set) var savedFavoriteComedians: [Components.Schemas.ComedianSearchItem] = []
    @Published private(set) var savedFavoritesPhase: SavedFavoritesPhase = .idle

    private var hasLoadedSavedFavorites = false

    func value(for uuid: String, fallback: Bool? = nil) -> Bool {
        values[uuid] ?? fallback ?? false
    }

    func storedValue(for uuid: String) -> Bool? {
        values[uuid]
    }

    func isPending(_ uuid: String) -> Bool {
        pending.contains(uuid)
    }

    func resetSavedFavorites() {
        hasLoadedSavedFavorites = false
        savedFavoriteComedians = []
        savedFavoritesPhase = .idle
    }

    func seed(uuid: String, value: Bool?) {
        guard let value, values[uuid] == nil else { return }
        values[uuid] = value
    }

    func overwrite(uuid: String, value: Bool?) {
        guard let value else { return }
        values[uuid] = value
    }

    func loadSavedFavorites(
        apiClient: Client,
        authManager: AuthManager,
        force: Bool = false
    ) async {
        guard authManager.currentSession != nil else {
            resetSavedFavorites()
            return
        }
        if hasLoadedSavedFavorites && !force {
            return
        }

        savedFavoritesPhase = .loading

        do {
            let output = try await apiClient.getFavorites()
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                savedFavoriteComedians = response.data
                hasLoadedSavedFavorites = true
                response.data.forEach { comedian in
                    values[comedian.uuid] = true
                }
                savedFavoritesPhase = response.data.isEmpty ? .empty : .loaded
            case .unauthorized(let unauthorized):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(
                    (try? unauthorized.body.json.error) ??
                        "Your session expired. Sign in again to load favorites."
                )
            case .unprocessableContent(let invalidProfile):
                resetSavedFavorites()
                savedFavoritesPhase = .failure(
                    (try? invalidProfile.body.json.error) ??
                        "Your account needs to sign in again before loading favorites."
                )
            case .internalServerError(let serverError):
                savedFavoritesPhase = .failure(
                    (try? serverError.body.json.error) ??
                        "LaughTrack hit a server error while loading favorites."
                )
            case .undocumented(let status, _):
                savedFavoritesPhase = .failure(
                    "LaughTrack returned an unexpected favorites response (\(status))."
                )
            }
        } catch {
            guard !Task.isCancelled else { return }
            savedFavoritesPhase = .failure(
                "LaughTrack couldn’t reach the favorites service. Please try again."
            )
        }
    }

    func toggle(
        uuid: String,
        currentValue: Bool,
        apiClient: Client,
        authManager: AuthManager
    ) async -> ToggleResult {
        guard authManager.currentSession != nil else {
            return .signInRequired("Sign in from Settings to save favorite comedians.")
        }

        pending.insert(uuid)
        defer { pending.remove(uuid) }

        do {
            let response: Components.Schemas.FavoriteResponse
            if currentValue {
                let output = try await apiClient.removeFavorite(.init(path: .init(comedianId: uuid)))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            } else {
                let output = try await apiClient.addFavorite(.init(body: .json(.init(comedianId: uuid))))
                switch output {
                case .ok(let ok):
                    response = try ok.body.json
                case .unauthorized(let unauthorized):
                    return .signInRequired((try? unauthorized.body.json.error) ?? "Your session expired. Sign in again to save favorites.")
                case .badRequest(let badRequest):
                    return .failure((try? badRequest.body.json.error) ?? "LaughTrack couldn’t update that favorite.")
                case .notFound(let notFound):
                    return .failure((try? notFound.body.json.error) ?? "That comedian could not be found.")
                case .unprocessableContent(let invalidProfile):
                    return .failure((try? invalidProfile.body.json.error) ?? "Your account needs to sign in again before saving favorites.")
                case .internalServerError(let serverError):
                    return .failure((try? serverError.body.json.error) ?? "LaughTrack hit a server error while updating favorites.")
                case .undocumented(let status, _):
                    return .failure("LaughTrack returned an unexpected response (\(status)).")
                }
            }

            let nextValue = response.data.isFavorited
            values[uuid] = nextValue
            if nextValue {
                if let index = savedFavoriteComedians.firstIndex(where: { $0.uuid == uuid }) {
                    savedFavoriteComedians[index].isFavorite = true
                }
            } else {
                savedFavoriteComedians.removeAll { $0.uuid == uuid }
                if savedFavoriteComedians.isEmpty, hasLoadedSavedFavorites {
                    savedFavoritesPhase = .empty
                }
            }
            return .updated(nextValue)
        } catch {
            return .failure("LaughTrack couldn’t reach the favorites service. Please try again.")
        }
    }
}

@MainActor
final class ComediansDiscoveryModel: EntitySearchModel<String, Components.Schemas.ComedianSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        let query = normalizedQuery
        await super.reload(query: query, shouldDebounce: !query.isEmpty) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites)
        }
    }

    func loadMore(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.loadMore(query: normalizedQuery) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites)
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    private var normalizedQuery: String {
        searchText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func fetchPage(
        page: Int,
        query: String,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> LoadResult<DiscoverySearchResponse<Components.Schemas.ComedianSearchItem>> {
        do {
            if query.isEmpty {
                let output = try await apiClient.listComedians(
                    .init(
                        query: .init(
                            limit: Self.pageSize,
                            offset: page * Self.pageSize
                        )
                    )
                )

                switch output {
                case .ok(let ok):
                    let response = try ok.body.json
                    let items = response.data.map { comedian in
                        Components.Schemas.ComedianSearchItem(
                            id: comedian.id,
                            uuid: comedian.uuid,
                            name: comedian.name,
                            imageUrl: comedian.imageUrl,
                            socialData: comedian.socialData,
                            showCount: comedian.showCount,
                            isFavorite: favorites.storedValue(for: comedian.uuid)
                        )
                    }
                    return .success(
                        .init(
                            items: items,
                            total: response.data.count < Self.pageSize ? page * Self.pageSize + items.count : (page + 1) * Self.pageSize + 1
                        )
                    )
                case .badRequest(let badRequest):
                    return .failure(.init((try? badRequest.body.json.error) ?? "LaughTrack could not load comedians right now."))
                case .internalServerError(let serverError):
                    return .failure(.init((try? serverError.body.json.error) ?? "LaughTrack could not load comedians right now."))
                case .undocumented(let status, _):
                    return .failure(.init("LaughTrack returned an unexpected comedians response (\(status))."))
                }
            } else {
                let output = try await apiClient.searchComedians(
                    .init(
                        query: .init(
                            comedian: query.nonEmpty,
                            page: page,
                            size: Self.pageSize
                        ),
                        headers: .init(xTimezone: TimeZone.current.identifier)
                    )
                )

                switch output {
                case .ok(let ok):
                    let response = try ok.body.json
                    let items = response.data.map { comedian in
                        favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                        return comedian
                    }
                    return .success(
                        .init(
                            items: items,
                            total: response.total
                        )
                    )
                case .internalServerError(let serverError):
                    return .failure(.init((try? serverError.body.json.error) ?? "LaughTrack could not load comedians right now."))
                case .undocumented(let status, _):
                    return .failure(.init("LaughTrack returned an unexpected comedians response (\(status))."))
                }
            }
        } catch {
            guard !Task.isCancelled else {
                return .failure(.init("LaughTrack could not load comedians right now."))
            }
            return .failure(.init("LaughTrack could not reach the comedians service. Check your connection and try again."))
        }
    }
}

@MainActor
final class ClubsDiscoveryModel: EntitySearchModel<String, Components.Schemas.ClubSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""

    func reload(apiClient: Client) async {
        let query = normalizedQuery
        await super.reload(query: query, shouldDebounce: !query.isEmpty) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func loadMore(apiClient: Client) async {
        await super.loadMore(query: normalizedQuery) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    private var normalizedQuery: String {
        searchText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func fetchPage(
        page: Int,
        query: String,
        apiClient: Client
    ) async -> LoadResult<DiscoverySearchResponse<Components.Schemas.ClubSearchItem>> {
        do {
            if query.isEmpty {
                let output = try await apiClient.listClubs(
                    .init(
                        query: .init(
                            limit: Self.pageSize,
                            offset: page * Self.pageSize
                        )
                    )
                )

                switch output {
                case .ok(let ok):
                    let response = try ok.body.json
                    let items = response.data.map { club in
                        Components.Schemas.ClubSearchItem(
                            id: club.id,
                            address: club.address,
                            name: club.name,
                            zipCode: club.zipCode,
                            imageUrl: club.imageUrl,
                            showCount: nil,
                            isFavorite: nil,
                            city: nil,
                            state: nil,
                            phoneNumber: nil,
                            socialData: nil,
                            activeComedianCount: club.activeComedianCount,
                            distanceMiles: nil
                        )
                    }
                    return .success(
                        .init(
                            items: items,
                            total: response.data.count < Self.pageSize ? page * Self.pageSize + items.count : (page + 1) * Self.pageSize + 1
                        )
                    )
                case .badRequest(let badRequest):
                    return .failure(.init((try? badRequest.body.json.error) ?? "LaughTrack could not load clubs right now."))
                case .tooManyRequests(let tooManyRequests):
                    return .failure(.init((try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting club results right now."))
                case .internalServerError(let serverError):
                    return .failure(.init((try? serverError.body.json.error) ?? "LaughTrack could not load clubs right now."))
                case .undocumented(let status, _):
                    return .failure(.init("LaughTrack returned an unexpected clubs response (\(status))."))
                }
            } else {
                let output = try await apiClient.searchClubs(
                    .init(
                        query: .init(
                            club: query.nonEmpty,
                            page: page,
                            size: Self.pageSize
                        ),
                        headers: .init(xTimezone: TimeZone.current.identifier)
                    )
                )

                switch output {
                case .ok(let ok):
                    let response = try ok.body.json
                    return .success(
                        .init(
                            items: response.data,
                            total: response.total
                        )
                    )
                case .internalServerError(let serverError):
                    return .failure(.init((try? serverError.body.json.error) ?? "LaughTrack could not load clubs right now."))
                case .undocumented(let status, _):
                    return .failure(.init("LaughTrack returned an unexpected clubs response (\(status))."))
                }
            }
        } catch {
            guard !Task.isCancelled else {
                return .failure(.init("LaughTrack could not load clubs right now."))
            }
            return .failure(.init("LaughTrack could not reach the clubs service. Check your connection and try again."))
        }
    }
}

enum ShowDistanceOption: Int, CaseIterable, Identifiable {
    case nearby = 10
    case city = 25
    case regional = 50
    case roadTrip = 100

    var id: Int { rawValue }

    var title: String {
        "\(rawValue) mi"
    }

    static func from(distanceMiles: Int) -> Self {
        Self(rawValue: distanceMiles) ?? .city
    }
}

enum ShowSortOption: String, CaseIterable, Identifiable {
    case earliest = "date_asc"
    case latest = "date_desc"
    case popular = "popularity_desc"
    case budget = "price_asc"
    case premium = "price_desc"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .earliest:
            return "Earliest"
        case .latest:
            return "Latest"
        case .popular:
            return "Popular"
        case .budget:
            return "Low price"
        case .premium:
            return "High price"
        }
    }
}

struct ShowsDiscoveryQuery: Hashable {
    let comedian: String
    let club: String
    let zip: String
    let useDateRange: Bool
    let from: Date
    let to: Date
    let distance: ShowDistanceOption
    let sort: ShowSortOption

    var fromString: String? {
        guard useDateRange else { return nil }
        return ShowFormatting.apiDate(from)
    }

    var toString: String? {
        guard useDateRange else { return nil }
        return ShowFormatting.apiDate(to)
    }

    var sanitizedZip: String? {
        let digits = zip.filter(\.isNumber)
        guard digits.count == 5 else { return nil }
        return digits
    }

    var hasActiveFilters: Bool {
        !comedian.isEmpty ||
        !club.isEmpty ||
        sanitizedZip != nil ||
        useDateRange ||
        sort != .earliest
    }
}

@MainActor
final class ShowsDiscoveryModel: EntitySearchModel<ShowsDiscoveryQuery, Components.Schemas.Show>, SearchRootQueryReceivable {
    private static let pageSize = 10

    @Published var zipCodeDraft = ""
    @Published var comedianSearchText = ""
    @Published var clubSearchText = ""
    @Published var useDateRange = false
    @Published var fromDate = Calendar.current.startOfDay(for: Date())
    @Published var toDate = Calendar.current.date(byAdding: .day, value: 14, to: Calendar.current.startOfDay(for: Date())) ?? Date()
    @Published var distance: ShowDistanceOption = .city {
        didSet {
            guard let activeNearbyPreference, activeNearbyPreference.distanceMiles != distance.rawValue else { return }
            nearbyLocationController.updateDistanceMiles(distance.rawValue)
        }
    }
    @Published var sort: ShowSortOption = .earliest
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var nearbyStatusMessage: String?
    @Published private(set) var zipCapTriggered = false
    @Published private(set) var isResolvingCurrentLocation = false

    private let nearbyLocationController: NearbyLocationController
    private var nearbyPreferenceCancellable: AnyCancellable?
    private var nearbyStatusCancellable: AnyCancellable?
    private var nearbyLoadingCancellable: AnyCancellable?
    init(nearbyLocationController: NearbyLocationController) {
        self.nearbyLocationController = nearbyLocationController
        super.init()
        applyNearbyPreference(nearbyLocationController.preference)
        nearbyPreferenceCancellable = nearbyLocationController.$preference
            .sink { [weak self] preference in
                self?.applyNearbyPreference(preference)
            }
        nearbyStatusCancellable = nearbyLocationController.$statusMessage
            .sink { [weak self] message in
                self?.nearbyStatusMessage = message
            }
        nearbyLoadingCancellable = nearbyLocationController.$isResolvingCurrentLocation
            .sink { [weak self] isResolving in
                self?.isResolvingCurrentLocation = isResolving
            }
    }

    var requestKey: ShowsDiscoveryQuery {
        let trimmedTo = max(toDate, fromDate)
        return .init(
            comedian: comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            club: clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            zip: activeNearbyPreference?.zipCode ?? "",
            useDateRange: useDateRange,
            from: fromDate,
            to: trimmedTo,
            distance: distance,
            sort: sort
        )
    }

    var timezoneLabel: String {
        let timezone = TimeZone.autoupdatingCurrent
        return timezone.localizedName(for: .shortStandard, locale: .current) ?? timezone.identifier
    }

    func reload(apiClient: Client) async {
        let query = requestKey
        await super.reload(query: query, shouldDebounce: query.hasActiveFilters) { [weak self] page, query in
            guard let self else { return .failure(.init("LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func loadMore(apiClient: Client) async {
        await super.loadMore(query: requestKey) { [weak self] page, query in
            guard let self else { return .failure(.init("LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient)
        }
    }

    func applySearchRootQuery(_ query: String) {
        // The unified root currently treats show search as a comedian-name query.
        // Venue-name discovery remains explicit in the Clubs pivot.
        comedianSearchText = query
        clubSearchText = ""
    }

    func clearLocation() {
        zipCodeDraft = ""
        nearbyStatusMessage = nil
        nearbyLocationController.clear()
    }

    func applyManualZip() -> Bool {
        guard !zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            clearLocation()
            return true
        }

        return nearbyLocationController.applyManualZip(zipCodeDraft, distanceMiles: distance.rawValue)
    }

    @discardableResult
    func useCurrentLocation() async -> Bool {
        await nearbyLocationController.useCurrentLocation(distanceMiles: distance.rawValue)
    }

    private func fetchPage(
        page: Int,
        query: ShowsDiscoveryQuery,
        apiClient: Client
    ) async -> LoadResult<DiscoverySearchResponse<Components.Schemas.Show>> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: query.sanitizedZip,
                        from: query.fromString,
                        to: query.toString,
                        page: page,
                        size: Self.pageSize,
                        comedian: query.comedian.nonEmpty,
                        club: query.club.nonEmpty,
                        distance: query.sanitizedZip == nil ? nil : query.distance.rawValue,
                        sort: query.sort.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                zipCapTriggered = response.zipCapTriggered
                return .success(
                    .init(
                        items: response.data,
                        total: response.total
                    )
                )
            case .badRequest(let badRequest):
                return .failure(.init((try? badRequest.body.json.error) ?? "LaughTrack could not apply those show filters."))
            case .internalServerError(let serverError):
                return .failure(.init((try? serverError.body.json.error) ?? "LaughTrack could not load shows right now."))
            case .undocumented(let status, _):
                return .failure(.init("LaughTrack returned an unexpected response (\(status))."))
            }
        } catch {
            guard !Task.isCancelled else {
                return .failure(.init("LaughTrack could not load shows right now."))
            }
            return .failure(.init("LaughTrack could not reach the shows search service. Check your connection and try again."))
        }
    }

    private func applyNearbyPreference(_ preference: NearbyPreference?) {
        activeNearbyPreference = preference

        if let preference {
            zipCodeDraft = preference.zipCode
            distance = .from(distanceMiles: preference.distanceMiles)
        } else if zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            zipCodeDraft = ""
            distance = .city
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
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        _showsModel = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: NearbyLocationController(
                    store: nearbyPreferenceStore,
                    resolver: LaughTrackCore.CurrentLocationZipResolver()
                )
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

struct ShowsSearchScreen: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @StateObject private var model: ShowsDiscoveryModel

    init(
        apiClient: Client,
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        _model = StateObject(
            wrappedValue: ShowsDiscoveryModel(
                nearbyLocationController: NearbyLocationController(
                    store: nearbyPreferenceStore,
                    resolver: LaughTrackCore.CurrentLocationZipResolver()
                )
            )
        )
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                LaughTrackSectionHeader(
                    eyebrow: "Shows Search",
                    title: "Search live shows",
                    subtitle: "Run focused show searches against the live LaughTrack backend, keep result states explicit, and jump straight into the matching show detail screen."
                )

                HStack(spacing: theme.spacing.sm) {
                    LaughTrackBadge("Live results", systemImage: "dot.radiowaves.left.and.right", tone: .highlight)
                    LaughTrackBadge("Show details", systemImage: "ticket.fill", tone: .neutral)
                    LaughTrackBadge("Mobile filters", systemImage: "slider.horizontal.3", tone: .accent)
                }

                ShowsDiscoveryView(apiClient: apiClient, model: model)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, theme.laughTrackTokens.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .background(
            theme.laughTrackTokens.gradients.heroWash
                .frame(maxHeight: 220)
                .ignoresSafeArea(edges: .top),
            alignment: .top
        )
        .navigationTitle("Search Shows")
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
    }
}

struct ClubsSearchScreen: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @StateObject private var model = ClubsDiscoveryModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                LaughTrackSectionHeader(
                    eyebrow: "Clubs Search",
                    title: "Search live clubs",
                    subtitle: "Browse live venue results from the LaughTrack backend, keep search states explicit, and move straight into each club detail screen."
                )

                HStack(spacing: theme.spacing.sm) {
                    LaughTrackBadge("Live results", systemImage: "dot.radiowaves.left.and.right", tone: .highlight)
                    LaughTrackBadge("Club details", systemImage: "building.2.fill", tone: .neutral)
                    LaughTrackBadge("Mobile browse", systemImage: "iphone", tone: .accent)
                }

                ClubsDiscoveryView(apiClient: apiClient, model: model)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, theme.laughTrackTokens.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubsSearchScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .background(
            theme.laughTrackTokens.gradients.heroWash
                .frame(maxHeight: 220)
                .ignoresSafeArea(edges: .top),
            alignment: .top
        )
        .navigationTitle("Search Clubs")
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
    }
}

struct ComediansSearchScreen: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @StateObject private var model = ComediansDiscoveryModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.xl) {
                LaughTrackSectionHeader(
                    eyebrow: "Comedians Search",
                    title: "Search live comedians",
                    subtitle: "Query the live LaughTrack backend for comedians, keep loading and failure states explicit, and move directly into each comedian detail screen."
                )

                HStack(spacing: theme.spacing.sm) {
                    LaughTrackBadge("Live results", systemImage: "dot.radiowaves.left.and.right", tone: .highlight)
                    LaughTrackBadge("Comedian details", systemImage: "music.mic", tone: .neutral)
                    LaughTrackBadge("Mobile discovery", systemImage: "iphone", tone: .accent)
                }

                ComediansDiscoveryView(apiClient: apiClient, model: model)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, theme.laughTrackTokens.spacing.heroPadding)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .background(
            theme.laughTrackTokens.gradients.heroWash
                .frame(maxHeight: 220)
                .ignoresSafeArea(edges: .top),
            alignment: .top
        )
        .navigationTitle("Search Comedians")
        .modifier(LaughTrackNavigationChrome(background: theme.laughTrackTokens.colors.canvas))
    }
}

private protocol CurrentLocationZipResolving {
    func resolveZipCode() async throws -> String
}

private enum CurrentLocationZipResolverError: LocalizedError {
    case disabled
    case denied
    case restricted
    case unavailable
    case missingPostalCode

    var errorDescription: String? {
        switch self {
        case .disabled:
            return "Location Services are disabled on this device."
        case .denied:
            return "LaughTrack does not have location access yet. Enable it in Settings or enter a ZIP instead."
        case .restricted:
            return "Location access is restricted on this device. Enter a ZIP instead."
        case .unavailable:
            return "LaughTrack could not determine your current location."
        case .missingPostalCode:
            return "LaughTrack found your location but could not resolve a nearby ZIP code."
        }
    }
}

@MainActor
private final class CurrentLocationZipResolver: NSObject, @preconcurrency CLLocationManagerDelegate, CurrentLocationZipResolving {
    private let locationManager = CLLocationManager()
    private let geocoder = CLGeocoder()
    private var authorizationContinuation: CheckedContinuation<Void, Error>?
    private var locationContinuation: CheckedContinuation<CLLocation, Error>?

    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    func resolveZipCode() async throws -> String {
        guard CLLocationManager.locationServicesEnabled() else {
            throw CurrentLocationZipResolverError.disabled
        }

        try await requestAuthorizationIfNeeded()
        let location = try await requestLocation()
        let placemarks = try await geocoder.reverseGeocodeLocation(location)

        guard
            let postalCode = placemarks.first?.postalCode,
            let normalized = NearbyPreferenceStore.validZip(from: postalCode)
        else {
            throw CurrentLocationZipResolverError.missingPostalCode
        }

        return normalized
    }

    private func requestAuthorizationIfNeeded() async throws {
        switch locationManager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            return
        case .notDetermined:
            try await withCheckedThrowingContinuation { continuation in
                authorizationContinuation = continuation
                locationManager.requestWhenInUseAuthorization()
            }
        case .denied:
            throw CurrentLocationZipResolverError.denied
        case .restricted:
            throw CurrentLocationZipResolverError.restricted
        @unknown default:
            throw CurrentLocationZipResolverError.unavailable
        }
    }

    private func requestLocation() async throws -> CLLocation {
        try await withCheckedThrowingContinuation { continuation in
            locationContinuation = continuation
            locationManager.requestLocation()
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        guard let continuation = authorizationContinuation else { return }

        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            authorizationContinuation = nil
            continuation.resume()
        case .denied:
            authorizationContinuation = nil
            continuation.resume(throwing: CurrentLocationZipResolverError.denied)
        case .restricted:
            authorizationContinuation = nil
            continuation.resume(throwing: CurrentLocationZipResolverError.restricted)
        case .notDetermined:
            break
        @unknown default:
            authorizationContinuation = nil
            continuation.resume(throwing: CurrentLocationZipResolverError.unavailable)
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let continuation = locationContinuation else { return }
        locationContinuation = nil

        guard let location = locations.last else {
            continuation.resume(throwing: CurrentLocationZipResolverError.unavailable)
            return
        }

        continuation.resume(returning: location)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: any Error) {
        guard let continuation = locationContinuation else { return }
        locationContinuation = nil
        continuation.resume(throwing: error)
    }
}

private struct HomeNearbyPage {
    let items: [Components.Schemas.Show]
    let total: Int
    let zipCapTriggered: Bool
}

@MainActor
private final class HomeNearbyDiscoveryModel: ObservableObject {
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
    private let locationResolver: any CurrentLocationZipResolving
    private var preferenceCancellable: AnyCancellable?
    private var loadedPreference: NearbyPreference?

    init(
        nearbyPreferenceStore: NearbyPreferenceStore,
        appStateStorage: AppStateStorageProtocol = AppStateStorage(),
        locationResolver: (any CurrentLocationZipResolving)? = nil
    ) {
        self.nearbyPreferenceStore = nearbyPreferenceStore
        self.appStateStorage = appStateStorage
        self.locationResolver = locationResolver ?? CurrentLocationZipResolver()
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
                    (try? badRequest.body.json.error) ?? "LaughTrack could not apply those nearby filters."
                )
            case .internalServerError(let serverError):
                phase = .failure(
                    (try? serverError.body.json.error) ?? "LaughTrack could not load nearby shows right now."
                )
            case .undocumented(let status, _):
                phase = .failure("LaughTrack returned an unexpected response (\(status)).")
            }
        } catch {
            guard !Task.isCancelled else { return }
            phase = .failure(
                "LaughTrack could not reach the nearby shows service. Check your connection and try again."
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
        nearbyPreferenceStore.clear()
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
        isResolvingLocation = true
        zipValidationMessage = nil
        locationMessage = nil
        defer { isResolvingLocation = false }

        do {
            let zipCode = try await locationResolver.resolveZipCode()
            nearbyPreferenceStore.setGeolocatedZip(
                zipCode,
                distanceMiles: activeNearbyPreference?.distanceMiles
            )
            isEditingZip = false
        } catch {
            locationMessage = error.localizedDescription
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
        nearbyPreferenceStore: NearbyPreferenceStore
    ) {
        self.apiClient = apiClient
        _model = StateObject(
            wrappedValue: HomeNearbyDiscoveryModel(
                nearbyPreferenceStore: nearbyPreferenceStore
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
            case .failure(let message):
                ErrorCard(message: message) {
                    await model.refresh(apiClient: apiClient)
                }
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
                title: "Nearby discovery is paused",
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

struct ShowsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ShowsDiscoveryModel
    var displaysSearchFields = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Shows",
                    title: "Shows nearby",
                    subtitle: "Keep filters close and results dense."
                )

                if displaysSearchFields {
                    SearchField(
                        title: "Comedian",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.comedianSearchText
                    )

                    SearchField(
                        title: "Club",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.clubSearchText
                    )
                }

                ShowFiltersPanel(model: model)

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading shows")
                case .failure(let message):
                    ErrorCard(title: "Couldn’t load shows", message: message) {
                        Task {
                            await model.reload(apiClient: apiClient)
                        }
                    }
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(title: "No shows yet", message: emptyMessage)
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)
                            ShowsSearchMeta(model: model, zipCapTriggered: model.zipCapTriggered)

                            ForEach(result.items, id: \.id) { show in
                                Button {
                                    coordinator.open(.show(show.id))
                                } label: {
                                    ShowRow(show: show)
                                }
                                .buttonStyle(.plain)
                                .accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))
                            }

                            if let paginationMessage = model.paginationMessage {
                                InlineStatusMessage(message: paginationMessage)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more shows",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey) {
            await model.reload(apiClient: apiClient)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
    }

    private var emptyMessage: String {
        if !model.comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
            !model.clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return "No shows matched this search. Try another comedian, club, or a broader date range."
        }

        if model.activeNearbyPreference != nil {
            return "No shows matched this ZIP code yet. Broaden the radius or clear location filters."
        }

        return "No shows are available right now."
    }
}

struct ComediansDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ComediansDiscoveryModel
    var displaysSearchInput = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @State private var feedbackMessage: String?

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Comedians",
                    title: "Comedians in rotation",
                    subtitle: "Scan favorites and upcoming sets without leaving Search."
                )

                if displaysSearchInput {
                    SearchField(
                        title: "Comedian name",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.searchText
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading comedians")
                case .failure(let message):
                    ErrorCard(title: "Couldn’t load comedians", message: message) {
                        Task {
                            await model.reload(apiClient: apiClient, favorites: favorites)
                        }
                    }
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No comedians yet",
                            message: model.searchText.isEmpty
                                ? "No comedians are available right now."
                                : "No comedians matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(result.items, id: \.uuid) { comedian in
                                ComedianRow(
                                    comedian: comedian,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage,
                                    openDetail: { coordinator.open(.comedian(comedian.id)) }
                                )
                                .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchResultButton(comedian.id))
                            }

                            if let paginationMessage = model.paginationMessage {
                                InlineStatusMessage(message: paginationMessage)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more comedians",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient, favorites: favorites)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.searchText) {
            await model.reload(apiClient: apiClient, favorites: favorites)
        }
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
        .accessibilityIdentifier(LaughTrackViewTestID.comediansSearchScreen)
    }
}

struct ClubsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ClubsDiscoveryModel
    var displaysSearchInput = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Clubs",
                    title: "Clubs in reach",
                    subtitle: "Keep venues dense, tappable, and easy to scan."
                )

                if displaysSearchInput {
                    SearchField(
                        title: "Club name",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.searchText
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading clubs")
                case .failure(let message):
                    ErrorCard(title: "Couldn’t load clubs", message: message) {
                        Task {
                            await model.reload(apiClient: apiClient)
                        }
                    }
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No clubs yet",
                            message: model.searchText.isEmpty
                                ? "No clubs are available right now."
                                : "No clubs matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(Array(result.items.enumerated()), id: \.offset) { _, club in
                                Button {
                                    if let id = club.id {
                                        coordinator.open(.club(id))
                                    }
                                } label: {
                                    ClubRow(club: club)
                                }
                                .buttonStyle(.plain)
                                .disabled(club.id == nil)
                                .accessibilityIdentifier(club.id.map(LaughTrackViewTestID.clubsSearchResultButton) ?? "laughtrack.clubs-search.result-missing-id")
                            }

                            if let paginationMessage = model.paginationMessage {
                                InlineStatusMessage(message: paginationMessage)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more clubs",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.searchText) {
            await model.reload(apiClient: apiClient)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubsSearchScreen)
    }
}

@MainActor
private final class ShowDetailModel: EntityDetailModel<Components.Schemas.ShowDetailResponse> {
    let showID: Int

    init(showID: Int) {
        self.showID = showID
    }

    func loadIfNeeded(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> LoadResult<Components.Schemas.ShowDetailResponse> {
        do {
            let output = try await apiClient.getShow(.init(path: .init(id: showID)))
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                for comedian in response.data.lineup ?? [] {
                    favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                }
                return .success(response)
            case .badRequest:
                return .failure(.init("LaughTrack could not load this show right now."))
            case .notFound:
                return .failure(.init("This show could not be found."))
            case .tooManyRequests:
                return .failure(.init("LaughTrack is rate-limiting show details right now."))
            case .internalServerError:
                return .failure(.init("LaughTrack hit a server error while loading this show."))
            case .undocumented(let status, _):
                return .failure(.init("LaughTrack returned an unexpected show detail response (\(status))."))
            }
        } catch {
            return .failure(.init("LaughTrack could not reach the show details service. Check your connection and try again."))
        }
    }
}

private struct ComedianDetailContent: Hashable {
    let comedian: Components.Schemas.ComedianDetail
    let upcomingShows: [Components.Schemas.Show]
    let relatedComedians: [Components.Schemas.ComedianLineup]
    let relatedContentMessage: String?
}

private struct ClubDetailContent: Hashable {
    let club: Components.Schemas.ClubDetail
    let upcomingShows: [Components.Schemas.Show]
    let featuredComedians: [Components.Schemas.ComedianLineup]
    let relatedContentMessage: String?
}

@MainActor
private final class ComedianDetailModel: EntityDetailModel<ComedianDetailContent> {
    private static let pageSize = 8
    let comedianID: Int

    init(comedianID: Int) {
        self.comedianID = comedianID
    }

    func loadIfNeeded(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    func reload(apiClient: Client, favorites: ComedianFavoriteStore) async {
        await super.reload {
            await self.fetch(apiClient: apiClient, favorites: favorites)
        }
    }

    private func fetch(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> LoadResult<ComedianDetailContent> {
        do {
            let output = try await apiClient.getComedian(.init(path: .init(id: comedianID)))
            switch output {
            case .ok(let ok):
                let comedian = try ok.body.json.data
                favorites.overwrite(uuid: comedian.uuid, value: favorites.value(for: comedian.uuid))
                return await loadRelatedContent(
                    for: comedian,
                    apiClient: apiClient,
                    favorites: favorites
                )
            case .badRequest:
                return .failure(.init("LaughTrack could not load this comedian right now."))
            case .notFound:
                return .failure(.init("This comedian could not be found."))
            case .internalServerError:
                return .failure(.init("LaughTrack hit a server error while loading this comedian."))
            case .undocumented(let status, _):
                return .failure(.init("LaughTrack returned an unexpected comedian detail response (\(status))."))
            }
        } catch {
            return .failure(.init("LaughTrack could not reach the comedian details service. Check your connection and try again."))
        }
    }

    private func loadRelatedContent(
        for comedian: Components.Schemas.ComedianDetail,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async -> LoadResult<ComedianDetailContent> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        from: ShowFormatting.apiDate(Date()),
                        page: 0,
                        size: Self.pageSize,
                        comedian: comedian.name,
                        sort: ShowSortOption.earliest.rawValue
                    )
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let relatedShows = response.data.filter { show in
                    guard let lineup = show.lineup else { return true }
                    return lineup.contains { lineupComedian in
                        lineupComedian.id == comedian.id || lineupComedian.uuid == comedian.uuid
                    }
                }

                for show in relatedShows {
                    for lineupComedian in show.lineup ?? [] {
                        favorites.seed(uuid: lineupComedian.uuid, value: lineupComedian.isFavorite)
                    }
                }

                var seenRelatedComedians = Set<String>()
                let relatedComedians = relatedShows
                    .flatMap { $0.lineup ?? [] }
                    .filter { lineupComedian in
                        lineupComedian.id != comedian.id && lineupComedian.uuid != comedian.uuid
                    }
                    .filter { lineupComedian in
                        seenRelatedComedians.insert(lineupComedian.uuid).inserted
                    }

                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: relatedShows,
                        relatedComedians: relatedComedians,
                        relatedContentMessage: nil
                    )
                )
            case .badRequest:
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack could not load the comedian's upcoming shows right now."
                    )
                )
            case .internalServerError:
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack hit a server error while loading related shows."
                    )
                )
            case .undocumented(let status, _):
                return .success(
                    .init(
                        comedian: comedian,
                        upcomingShows: [],
                        relatedComedians: [],
                        relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status))."
                    )
                )
            }
        } catch {
            return .success(
                .init(
                    comedian: comedian,
                    upcomingShows: [],
                    relatedComedians: [],
                    relatedContentMessage: "LaughTrack could not reach the related shows service. Check your connection and try again."
                )
            )
        }
    }
}

@MainActor
private final class ClubDetailModel: EntityDetailModel<ClubDetailContent> {
    private static let pageSize = 8
    let clubID: Int

    init(clubID: Int) {
        self.clubID = clubID
    }

    func loadIfNeeded(apiClient: Client) async {
        await super.loadIfNeeded {
            await self.fetch(apiClient: apiClient)
        }
    }

    func reload(apiClient: Client) async {
        await super.reload {
            await self.fetch(apiClient: apiClient)
        }
    }

    private func fetch(apiClient: Client) async -> LoadResult<ClubDetailContent> {
        do {
            let output = try await apiClient.getClub(.init(path: .init(id: clubID)))
            switch output {
            case .ok(let ok):
                return await loadRelatedContent(for: try ok.body.json.data, apiClient: apiClient)
            case .badRequest:
                return .failure(.init("LaughTrack could not load this club right now."))
            case .notFound:
                return .failure(.init("This club could not be found."))
            case .internalServerError:
                return .failure(.init("LaughTrack hit a server error while loading this club."))
            case .undocumented(let status, _):
                return .failure(.init("LaughTrack returned an unexpected club detail response (\(status))."))
            }
        } catch {
            return .failure(.init("LaughTrack could not reach the club details service. Check your connection and try again."))
        }
    }

    private func loadRelatedContent(
        for club: Components.Schemas.ClubDetail,
        apiClient: Client
    ) async -> LoadResult<ClubDetailContent> {
        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        from: ShowFormatting.apiDate(Date()),
                        page: 0,
                        size: Self.pageSize,
                        club: club.name,
                        sort: ShowSortOption.earliest.rawValue
                    )
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let upcomingShows = response.data.filter { show in
                    (show.clubName ?? "").localizedCaseInsensitiveCompare(club.name) == .orderedSame
                }

                var seenComedians = Set<String>()
                let featuredComedians = upcomingShows
                    .flatMap { $0.lineup ?? [] }
                    .filter { comedian in
                        seenComedians.insert(comedian.uuid).inserted
                    }

                return .success(
                    .init(
                        club: club,
                        upcomingShows: upcomingShows,
                        featuredComedians: featuredComedians,
                        relatedContentMessage: nil
                    )
                )
            case .badRequest:
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack could not load this club’s upcoming shows right now."
                    )
                )
            case .internalServerError:
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack hit a server error while loading this club’s related content."
                    )
                )
            case .undocumented(let status, _):
                return .success(
                    .init(
                        club: club,
                        upcomingShows: [],
                        featuredComedians: [],
                        relatedContentMessage: "LaughTrack returned an unexpected related shows response (\(status))."
                    )
                )
            }
        } catch {
            return .success(
                .init(
                    club: club,
                    upcomingShows: [],
                    featuredComedians: [],
                    relatedContentMessage: "LaughTrack could not reach this club’s related content service. Check your connection and try again."
                )
            )
        }
    }
}

struct ShowDetailView: View {
    let showID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @StateObject private var model: ShowDetailModel
    @State private var feedbackMessage: String?

    init(showID: Int, apiClient: Client) {
        self.showID = showID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ShowDetailModel(showID: showID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message) {
                    await model.reload(apiClient: apiClient, favorites: favorites)
                }
                .padding()
            case .success(let response):
                let show = response.data
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: show.name ?? "Untitled show",
                        subtitle: ShowFormatting.detailDate(show.date, timezoneID: show.timezone),
                        imageURL: show.imageUrl,
                        badges: showHeroBadges(show: show)
                    )

                    if let address = show.address ?? show.club.address {
                        DetailInfoCard(eyebrow: "Venue", title: show.club.name, subtitle: "Tap this card to open the full club detail.", rows: [
                            DetailInfoRow(label: "Address", value: address),
                            DetailInfoRow(label: "Room", value: show.room),
                            DetailInfoRow(label: "Distance", value: ShowFormatting.distance(show.distanceMiles))
                        ])
                        .onTapGesture {
                            coordinator.open(.club(show.club.id))
                        }
                    }

                    if let description = show.description, !description.isEmpty {
                        DetailTextCard(eyebrow: "Editor’s note", title: "About this show", text: description)
                    }

                    ShowCTASection(show: show) { url in
                        openURL(url)
                    }

                    ShowLineupSection(
                        lineup: show.lineup ?? [],
                        apiClient: apiClient,
                        feedbackMessage: $feedbackMessage
                    ) { comedian in
                        coordinator.open(.comedian(comedian.id))
                    }

                    RelatedShowsSection(relatedShows: response.relatedShows) { related in
                        coordinator.open(.show(related.id))
                    }
                }
                .padding()
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Show")
        .modifier(InlineNavigationTitle())
        .task {
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func showHeroBadges(show: Components.Schemas.ShowDetail) -> [DetailHeroBadge] {
        var badges = [
            DetailHeroBadge(
                title: show.club.name,
                systemImage: "building.2.fill",
                tone: .highlight
            )
        ]

        if let distance = ShowFormatting.distance(show.distanceMiles) {
            badges.append(
                DetailHeroBadge(
                    title: distance,
                    systemImage: "location.fill",
                    tone: .neutral
                )
            )
        }

        if show.soldOut == true {
            badges.append(
                DetailHeroBadge(
                    title: "Sold out",
                    systemImage: "ticket.fill",
                    tone: .warning
                )
            )
        }

        return badges
    }
}

private struct ShowLineupSection: View {
    let lineup: [Components.Schemas.ComedianLineup]
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: (Components.Schemas.ComedianLineup) -> Void

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Lineup",
                    title: "Tonight’s bill",
                    subtitle: "Tap any comic to open their native detail page."
                )

                if lineup.isEmpty {
                    EmptyCard(message: "Lineup details are not available yet.")
                } else {
                    ForEach(lineup, id: \.uuid) { comedian in
                        ComedianLineupRow(
                            comedian: comedian,
                            apiClient: apiClient,
                            feedbackMessage: $feedbackMessage,
                            openDetail: { openDetail(comedian) }
                        )
                    }
                }
            }
        }
    }
}

private struct RelatedShowsSection: View {
    let relatedShows: [Components.Schemas.Show]
    let openDetail: (Components.Schemas.Show) -> Void

    var body: some View {
        LaughTrackCard(tone: .muted) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Keep browsing",
                    title: "Related shows",
                    subtitle: "More dates from nearby rooms and linked talent."
                )

                if relatedShows.isEmpty {
                    EmptyCard(message: "No related shows are available yet.")
                } else {
                    ForEach(relatedShows, id: \.id) { related in
                        Button {
                            openDetail(related)
                        } label: {
                            ShowRow(show: related)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

struct ComedianDetailView: View {
    let comedianID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL

    @StateObject private var model: ComedianDetailModel
    @State private var feedbackMessage: String?

    init(comedianID: Int, apiClient: Client) {
        self.comedianID = comedianID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ComedianDetailModel(comedianID: comedianID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message) {
                    await model.reload(apiClient: apiClient, favorites: favorites)
                }
                .padding()
            case .success(let content):
                let comedian = content.comedian
                let isFavorite = favorites.value(for: comedian.uuid)
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: comedian.name,
                        subtitle: content.upcomingShows.isEmpty ? "Comedian detail" : "\(content.upcomingShows.count) upcoming show\(content.upcomingShows.count == 1 ? "" : "s")",
                        imageURL: comedian.imageUrl,
                        badges: comedianHeroBadges(comedian: comedian, upcomingShowCount: content.upcomingShows.count)
                    )

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Saved comics",
                                title: "Favorite",
                                subtitle: "Carry this comic back into discovery without leaving the detail flow."
                            )
                            HStack {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(isFavorite ? "In your favorites" : "Not saved yet")
                                        .font(theme.laughTrackTokens.typography.cardTitle)
                                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                                    Text("Saved comedians stay consistent across discovery and show lineups.")
                                        .font(theme.laughTrackTokens.typography.body)
                                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                                }
                                Spacer()
                                FavoriteButton(
                                    isFavorite: isFavorite,
                                    isPending: favorites.isPending(comedian.uuid)
                                ) {
                                    await toggleFavorite(name: comedian.name, uuid: comedian.uuid, currentValue: isFavorite)
                                }
                            }
                        }
                    }

                    DetailInfoCard(
                        eyebrow: "Profile",
                        title: "What LaughTrack knows",
                        subtitle: "Live profile details come from the API contract and stay grounded in the comedian's active links.",
                        rows: comedianProfileRows(comedian: comedian, upcomingShowCount: content.upcomingShows.count)
                    )

                    SocialLinkSection(socialData: comedian.socialData) { url in
                        openURL(url)
                    }

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Upcoming shows",
                                title: "Catch them live",
                                subtitle: "Every result here comes from the live shows search filtered to this comedian."
                            )

                            if let relatedContentMessage = content.relatedContentMessage {
                                InlineStatusMessage(message: relatedContentMessage)
                            }

                            if content.upcomingShows.isEmpty {
                                EmptyCard(message: "No upcoming shows are available for this comedian right now.")
                            } else {
                                ForEach(content.upcomingShows, id: \.id) { show in
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

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Related comedians",
                                title: "People sharing the bill",
                                subtitle: "When lineup data is available, you can hop straight into the next comedian detail page."
                            )

                            if content.relatedComedians.isEmpty {
                                EmptyCard(message: "No related comedians are available yet.")
                            } else {
                                ForEach(content.relatedComedians, id: \.uuid) { relatedComedian in
                                    ComedianLineupRow(
                                        comedian: relatedComedian,
                                        apiClient: apiClient,
                                        feedbackMessage: $feedbackMessage,
                                        openDetail: { coordinator.open(.comedian(relatedComedian.id)) }
                                    )
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .accessibilityIdentifier(LaughTrackViewTestID.comedianDetailScreen)
        .navigationTitle("Comedian")
        .modifier(InlineNavigationTitle())
        .task {
            await model.loadIfNeeded(apiClient: apiClient, favorites: favorites)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func toggleFavorite(name: String, uuid: String, currentValue: Bool) async {
        let result = await favorites.toggle(
            uuid: uuid,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )

        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: name, isFavorite: next)
        case .signInRequired(let message), .failure(let message):
            feedbackMessage = message
        }
    }

    private func comedianHeroBadges(
        comedian: Components.Schemas.ComedianDetail,
        upcomingShowCount: Int
    ) -> [DetailHeroBadge] {
        var badges = [DetailHeroBadge(title: "Comedian detail", systemImage: "music.mic", tone: .highlight)]

        if upcomingShowCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(upcomingShowCount) upcoming",
                    systemImage: "calendar",
                    tone: .neutral
                )
            )
        }

        if let audienceReach = audienceReachText(for: comedian.socialData) {
            badges.append(
                DetailHeroBadge(
                    title: audienceReach,
                    systemImage: "person.3.fill",
                    tone: .accent
                )
            )
        }

        if let website = comedian.socialData.website, !website.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Website on file",
                    systemImage: "link",
                    tone: .neutral
                )
            )
        }

        return badges
    }

    private func comedianProfileRows(
        comedian: Components.Schemas.ComedianDetail,
        upcomingShowCount: Int
    ) -> [DetailInfoRow] {
        [
            DetailInfoRow(label: "Upcoming", value: upcomingShowCount == 0 ? "No live dates returned yet" : "\(upcomingShowCount) shows"),
            DetailInfoRow(label: "Audience", value: audienceReachText(for: comedian.socialData)),
            DetailInfoRow(label: "Instagram", value: socialHandle(comedian.socialData.instagramAccount, prefix: "@")),
            DetailInfoRow(label: "TikTok", value: socialHandle(comedian.socialData.tiktokAccount, prefix: "@")),
            DetailInfoRow(label: "YouTube", value: socialHandle(comedian.socialData.youtubeAccount, prefix: "@")),
            DetailInfoRow(label: "Website", value: comedian.socialData.website),
            DetailInfoRow(label: "Linktree", value: comedian.socialData.linktree)
        ]
    }

    private func audienceReachText(for socialData: Components.Schemas.SocialData) -> String? {
        let followerCount =
            (socialData.instagramFollowers ?? 0) +
            (socialData.tiktokFollowers ?? 0) +
            (socialData.youtubeFollowers ?? 0)

        guard followerCount > 0 else { return nil }
        return "\(followerCount.formatted(.number.notation(.compactName))) followers"
    }

    private func socialHandle(_ handle: String?, prefix: String) -> String? {
        guard let handle, !handle.isEmpty else { return nil }
        return handle.hasPrefix(prefix) ? handle : "\(prefix)\(handle)"
    }
}

struct ClubDetailView: View {
    let clubID: Int
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme
    @Environment(\.openURL) private var openURL
    @StateObject private var model: ClubDetailModel
    @State private var feedbackMessage: String?

    init(clubID: Int, apiClient: Client) {
        self.clubID = clubID
        self.apiClient = apiClient
        _model = StateObject(wrappedValue: ClubDetailModel(clubID: clubID))
    }

    var body: some View {
        ScrollView {
            switch model.phase {
            case .idle, .loading:
                LoadingCard()
                    .padding()
            case .failure(let message):
                ErrorCard(message: message) {
                    await model.reload(apiClient: apiClient)
                }
                .padding()
            case .success(let content):
                let club = content.club
                VStack(alignment: .leading, spacing: 20) {
                    DetailHero(
                        title: club.name,
                        subtitle: content.upcomingShows.isEmpty ? (club.zipCode ?? "Club detail") : "\(content.upcomingShows.count) upcoming show\(content.upcomingShows.count == 1 ? "" : "s")",
                        imageURL: club.imageUrl,
                        badges: clubHeroBadges(club: club, upcomingShowCount: content.upcomingShows.count, featuredComedianCount: content.featuredComedians.count)
                    )

                    DetailInfoCard(eyebrow: "Club details", title: "Venue", subtitle: "Core contact information comes directly from the live club endpoint.", rows: [
                        DetailInfoRow(label: "Address", value: club.address),
                        DetailInfoRow(label: "ZIP", value: club.zipCode),
                        DetailInfoRow(label: "Phone", value: club.phoneNumber)
                    ])

                    DetailLinkCard(
                        eyebrow: "Actions",
                        title: "Take the next step",
                        subtitle: "Jump out to the venue’s website, maps, or phone line when that data is available.",
                        links: clubActionLinks(club: club),
                        openURL: { url in openURL(url) }
                    )

                    LaughTrackCard {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Upcoming shows",
                                title: "What’s on at this room",
                                subtitle: "Live show results are filtered to this club so you can jump straight into a date."
                            )

                            if let relatedContentMessage = content.relatedContentMessage {
                                InlineStatusMessage(message: relatedContentMessage)
                            }

                            if content.upcomingShows.isEmpty {
                                EmptyCard(message: "No upcoming shows are available for this club right now.")
                            } else {
                                ForEach(content.upcomingShows, id: \.id) { show in
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

                    LaughTrackCard(tone: .muted) {
                        VStack(alignment: .leading, spacing: 12) {
                            LaughTrackSectionHeader(
                                eyebrow: "Featured comedians",
                                title: "Artists on upcoming bills",
                                subtitle: "When lineup data is available, you can move straight from the club profile into comedian details."
                            )

                            if content.featuredComedians.isEmpty {
                                EmptyCard(message: "No featured comedians are available for this club yet.")
                            } else {
                                ForEach(content.featuredComedians, id: \.uuid) { comedian in
                                    ComedianLineupRow(
                                        comedian: comedian,
                                        apiClient: apiClient,
                                        feedbackMessage: $feedbackMessage,
                                        openDetail: { coordinator.open(.comedian(comedian.id)) }
                                    )
                                }
                            }
                        }
                    }
                }
                .padding()
            }
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubDetailScreen)
        .background(theme.laughTrackTokens.colors.canvas.ignoresSafeArea())
        .navigationTitle("Club")
        .modifier(InlineNavigationTitle())
        .task {
            await model.loadIfNeeded(apiClient: apiClient)
        }
        .alert("LaughTrack", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
    }

    private func clubHeroBadges(
        club: Components.Schemas.ClubDetail,
        upcomingShowCount: Int,
        featuredComedianCount: Int
    ) -> [DetailHeroBadge] {
        var badges = [DetailHeroBadge(title: "Club detail", systemImage: "building.2.fill", tone: .highlight)]

        if upcomingShowCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(upcomingShowCount) upcoming",
                    systemImage: "calendar",
                    tone: .neutral
                )
            )
        }

        if featuredComedianCount > 0 {
            badges.append(
                DetailHeroBadge(
                    title: "\(featuredComedianCount) comics",
                    systemImage: "music.mic",
                    tone: .accent
                )
            )
        }

        if !club.address.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Address on file",
                    systemImage: "mappin.and.ellipse",
                    tone: .neutral
                )
            )
        }

        if let phoneNumber = club.phoneNumber, !phoneNumber.isEmpty {
            badges.append(
                DetailHeroBadge(
                    title: "Call venue",
                    systemImage: "phone.fill",
                    tone: .accent
                )
            )
        }

        return badges
    }

    private func clubActionLinks(club: Components.Schemas.ClubDetail) -> [DetailLink] {
        [
            DetailLink(title: "Visit website", url: URL.normalizedExternalURL(club.website)),
            DetailLink(title: "Open in Maps", url: URL.mapsURL(for: club.address)),
            DetailLink(title: "Call venue", url: URL.phoneURL(club.phoneNumber))
        ]
    }
}

private struct ShowCTASection: View {
    @Environment(\.appTheme) private var theme

    let show: Components.Schemas.ShowDetail
    let openURL: (URL) -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let primaryURL = URL.normalizedExternalURL(show.cta.url) ?? URL.normalizedExternalURL(show.showPageUrl)
        let fallbackURL = URL.normalizedExternalURL(show.showPageUrl)

        LaughTrackCard(tone: show.cta.isSoldOut ? .muted : .accent) {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Tickets",
                    title: show.cta.isSoldOut ? "Join the wait for the next one" : "Secure your seat",
                    subtitle: show.cta.isSoldOut ? "This show is marked sold out, but the venue path still stays visible." : "Primary and fallback CTAs use the same branded button language as discovery."
                )

                if let primaryURL {
                    LaughTrackButton(
                        show.cta.label,
                        systemImage: "arrow.up.right",
                        tone: show.cta.isSoldOut ? .secondary : .primary
                    ) {
                        openURL(primaryURL)
                    }
                    .disabled(show.cta.isSoldOut)
                } else {
                    EmptyCard(message: "Tickets are not linked yet for this show.")
                }

                if let fallbackURL, primaryURL != fallbackURL {
                    LaughTrackButton("Open show page", systemImage: "safari", tone: .tertiary) {
                        openURL(fallbackURL)
                    }
                }

                if let tickets = show.tickets, !tickets.isEmpty {
                    VStack(spacing: 10) {
                        ForEach(Array(tickets.enumerated()), id: \.offset) { index, ticket in
                            LaughTrackCard {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(ticket._type ?? "Ticket option \(index + 1)")
                                            .font(laughTrack.typography.action)
                                            .foregroundStyle(laughTrack.colors.textPrimary)
                                        if let price = ticket.price {
                                            Text(price, format: .currency(code: "USD"))
                                                .font(laughTrack.typography.metadata)
                                                .foregroundStyle(laughTrack.colors.textSecondary)
                                        }
                                    }
                                    Spacer()
                                    if let url = URL.normalizedExternalURL(ticket.purchaseUrl) {
                                        LaughTrackButton(
                                            ticket.soldOut == true ? "Sold out" : "Open",
                                            systemImage: ticket.soldOut == true ? "xmark.circle" : "arrow.up.right",
                                            tone: ticket.soldOut == true ? .secondary : .tertiary,
                                            fullWidth: false
                                        ) {
                                            openURL(url)
                                        }
                                        .disabled(ticket.soldOut == true)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private struct ComedianLineupRow: View {
    let comedian: Components.Schemas.ComedianLineup
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: theme.spacing.sm) {
            Button(action: openDetail) {
                LaughTrackResultRow(
                    title: comedian.name,
                    subtitle: nil,
                    metadata: ["\(comedian.showCount ?? 0) upcoming shows"],
                    systemImage: "music.mic",
                    imageURL: comedian.imageUrl,
                    showsDisclosureIndicator: false
                )
            }
            .buttonStyle(.plain)

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired(let message), .failure(let message):
                    feedbackMessage = message
                }
            }
        }
    }
}

private struct ComedianRow: View {
    let comedian: Components.Schemas.ComedianSearchItem
    let apiClient: Client
    @Binding var feedbackMessage: String?
    let openDetail: () -> Void

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var favorites: ComedianFavoriteStore
    @Environment(\.appTheme) private var theme

    var body: some View {
        let isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)

        HStack(spacing: theme.spacing.sm) {
            Button(action: openDetail) {
                LaughTrackResultRow(
                    title: comedian.name,
                    subtitle: SocialLink.links(from: comedian.socialData).first?.label,
                    metadata: ["\(comedian.showCount) upcoming"],
                    systemImage: "music.mic",
                    imageURL: comedian.imageUrl,
                    showsDisclosureIndicator: false
                )
            }
            .buttonStyle(.plain)

            FavoriteButton(
                isFavorite: isFavorite,
                isPending: favorites.isPending(comedian.uuid)
            ) {
                let result = await favorites.toggle(
                    uuid: comedian.uuid,
                    currentValue: isFavorite,
                    apiClient: apiClient,
                    authManager: authManager
                )
                switch result {
                case .updated(let next):
                    feedbackMessage = FavoriteFeedback.message(for: comedian.name, isFavorite: next)
                case .signInRequired(let message), .failure(let message):
                    feedbackMessage = message
                }
            }
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

private struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem

    var body: some View {
        LaughTrackResultRow(
            title: club.name ?? "Unknown club",
            subtitle: [club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable",
            metadata: [
                club.activeComedianCount.map { "\($0) active comedians" },
                club.showCount.map { "\($0) shows" },
            ].compactMap { $0 },
            systemImage: "building.2.fill",
            imageURL: club.imageUrl
        )
    }
}

private struct FavoriteButton: View {
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

private struct SearchField: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let prompt: String
    @Binding var text: String

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.xs) {
            Text(title)
                .font(theme.laughTrackTokens.typography.eyebrow)
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                .textCase(.uppercase)

            LaughTrackSearchField(placeholder: prompt, text: $text)
                .modifier(SearchFieldInputBehavior())
        }
    }
}

private struct ShowFiltersPanel: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(tone: .muted, density: .compact) {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                LaughTrackShelfHeader(
                    eyebrow: "Filters",
                    title: "Tune the search",
                    subtitle: "Keep location, sort, and dates in reach."
                )

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: theme.spacing.sm) {
                        LaughTrackBrowseChip("Live dates first", systemImage: "sparkles", tone: .accent)
                        LaughTrackBrowseChip("Dense result rows", systemImage: "rectangle.grid.1x2", tone: .neutral)
                        LaughTrackBrowseChip("Nearby aware", systemImage: "location.fill", tone: .neutral)
                    }
                }

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    Text("ZIP")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .textCase(.uppercase)

                    LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft)
                        .modifier(SearchFieldInputBehavior())
                        #if os(iOS)
                        .keyboardType(UIKeyboardType.numberPad)
                        #endif

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackButton("Use ZIP", systemImage: "location.fill", tone: .secondary, density: .compact, fullWidth: false) {
                                _ = model.applyManualZip()
                            }

                            CurrentLocationButton(isLoading: model.isResolvingCurrentLocation) {
                                await model.useCurrentLocation()
                            }

                            if model.activeNearbyPreference != nil {
                                LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact, fullWidth: false) {
                                    model.clearLocation()
                                }
                            }
                        }
                    }

                    if let nearbyStatusMessage = model.nearbyStatusMessage {
                        InlineStatusMessage(message: nearbyStatusMessage)
                    } else if let activeNearbyPreference = model.activeNearbyPreference {
                        LaughTrackContextRow(
                            leading: activeNearbyPreference.source == .manual ? "Saved ZIP" : "Current location",
                            trailing: "\(activeNearbyPreference.zipCode) • \(activeNearbyPreference.distanceMiles) mi"
                        )
                    }
                }

                HStack(spacing: theme.spacing.sm) {
                    Menu {
                        Picker("Sort", selection: $model.sort) {
                            ForEach(ShowSortOption.allCases) { option in
                                Text(option.title).tag(option)
                            }
                        }
                    } label: {
                        LaughTrackBrowseChip(
                            "Sort: \(model.sort.title)",
                            systemImage: "arrow.up.arrow.down",
                            tone: .neutral
                        )
                    }

                    if model.activeNearbyPreference != nil {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: theme.spacing.sm) {
                                ForEach(ShowDistanceOption.allCases) { option in
                                    Button {
                                        model.distance = option
                                    } label: {
                                        LaughTrackBrowseChip(
                                            option.title,
                                            systemImage: "location.north.line",
                                            tone: model.distance == option ? .selected : .neutral
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }
                }

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    HStack {
                        Text("Dates")
                            .font(laughTrack.typography.eyebrow)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)
                        Spacer()
                        Text(model.useDateRange ? "Custom window" : "Upcoming by default")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Toggle("Use date range", isOn: $model.useDateRange)
                        .font(laughTrack.typography.body)
                        .tint(laughTrack.colors.accent)

                    if model.useDateRange {
                        VStack(spacing: theme.spacing.md) {
                            DatePicker("From", selection: $model.fromDate, displayedComponents: .date)
                            DatePicker(
                                "To",
                                selection: Binding(
                                    get: { max(model.toDate, model.fromDate) },
                                    set: { model.toDate = max($0, model.fromDate) }
                                ),
                                in: model.fromDate...,
                                displayedComponents: .date
                            )
                        }
                        .font(laughTrack.typography.body)
                    }
                }
            }
        }
    }
}

private struct ShowsSearchMeta: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel
    let zipCapTriggered: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            LaughTrackContextRow(
                leading: "Times shown in \(model.timezoneLabel)",
                trailing: "\(activeFilters.count) filters"
            )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    ForEach(activeFilters, id: \.self) { filter in
                        LaughTrackBrowseChip(filter, tone: .neutral)
                    }
                }
            }

            if zipCapTriggered {
                LaughTrackInlineStateCard(
                    tone: .error,
                    title: "Location was broadened",
                    message: "That ZIP matched too many nearby locations. Try a tighter ZIP or clear the location filter.",
                    actionTitle: "Browse all shows"
                ) {
                    model.clearLocation()
                }
            }
        }
    }

    private var activeFilters: [String] {
        let query = model.requestKey
        var filters = ["Sort: \(query.sort.title)"]

        if let zip = query.sanitizedZip {
            filters.append("ZIP \(zip)")
            filters.append("Within \(query.distance.rawValue) mi")
        }

        if !query.comedian.isEmpty {
            filters.append("Comedian: \(query.comedian)")
        }

        if !query.club.isEmpty {
            filters.append("Club: \(query.club)")
        }

        if query.useDateRange, let from = query.fromString, let to = query.toString {
            filters.append("\(from) to \(to)")
        }

        return filters
    }
}

private struct SearchResultsSummary: View {
    @Environment(\.appTheme) private var theme

    let count: Int
    let total: Int

    var body: some View {
        LaughTrackContextRow(
            leading: "Showing \(count) of \(total)",
            trailing: "Live"
        )
    }
}

private struct InlineStatusMessage: View {
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

private struct CurrentLocationButton: View {
    let isLoading: Bool
    let action: () async -> Void

    var body: some View {
        LaughTrackButton(
            isLoading ? "Finding ZIP…" : "Use Current Location",
            systemImage: isLoading ? nil : "location.circle",
            tone: .secondary,
            density: .compact,
            fullWidth: false
        ) {
            Task {
                await action()
            }
        }
        .disabled(isLoading)
        .overlay(alignment: .trailing) {
            if isLoading {
                ProgressView()
                    .padding(.trailing, 12)
            }
        }
    }
}

private struct LoadMoreButton: View {
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

private struct DiscoveryCard<Content: View>: View {
    @Environment(\.appTheme) private var theme

    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                LaughTrackSectionHeader(eyebrow: "Discovery", title: title)
                content
            }
        }
    }
}

private struct DetailHeroBadge {
    let title: String
    let systemImage: String?
    let tone: LaughTrackBadgeTone
}

private struct DetailHero: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let subtitle: String
    let imageURL: String
    let badges: [DetailHeroBadge]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(tone: .accent) {
            VStack(alignment: .leading, spacing: 12) {
                RemoteImageView(urlString: imageURL, aspectRatio: 1.7)
                    .frame(maxWidth: .infinity)
                    .frame(height: 220)
                    .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
                Text(subtitle)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .textCase(.uppercase)
                Text(title)
                    .font(laughTrack.typography.hero)
                    .foregroundStyle(laughTrack.colors.textPrimary)

                if !badges.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            ForEach(Array(badges.enumerated()), id: \.offset) { _, badge in
                                LaughTrackBadge(
                                    badge.title,
                                    systemImage: badge.systemImage,
                                    tone: badge.tone
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private struct DetailInfoRow {
    let label: String
    let value: String?
}

private struct DetailInfoCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let rows: [DetailInfoRow]

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let visibleRows = rows.filter { ($0.value?.isEmpty == false) }

        return LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title, subtitle: subtitle)
                if visibleRows.isEmpty {
                    EmptyCard(message: "Details will appear here when LaughTrack has them.")
                } else {
                    ForEach(Array(visibleRows.enumerated()), id: \.offset) { _, row in
                        HStack(alignment: .top) {
                            Text(row.label)
                                .font(laughTrack.typography.metadata)
                                .foregroundStyle(laughTrack.colors.textSecondary)
                                .frame(width: 72, alignment: .leading)
                            Text(row.value ?? "")
                                .font(laughTrack.typography.body)
                                .foregroundStyle(laughTrack.colors.textPrimary)
                        }
                    }
                }
            }
        }
    }
}

private struct DetailTextCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let text: String

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title)
                Text(text)
                    .font(theme.laughTrackTokens.typography.body)
                    .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
            }
        }
    }
}

private struct DetailLink {
    let title: String
    let url: URL?
}

private struct DetailLinkCard: View {
    @Environment(\.appTheme) private var theme

    let eyebrow: String?
    let title: String
    let subtitle: String?
    let links: [DetailLink]
    let openURL: (URL) -> Void

    var body: some View {
        LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(eyebrow: eyebrow, title: title, subtitle: subtitle)
                ForEach(Array(links.enumerated()), id: \.offset) { _, link in
                    if let url = link.url {
                        LaughTrackButton(link.title, systemImage: "arrow.up.right", tone: .secondary) {
                            openURL(url)
                        }
                    }
                }
                if links.allSatisfy({ $0.url == nil }) {
                    EmptyCard(message: "No public links are available yet.")
                }
            }
        }
    }
}

private struct SocialLink: Identifiable {
    let id = UUID()
    let label: String
    let url: URL

    static func links(from socialData: Components.Schemas.SocialData) -> [SocialLink] {
        [
            ("Instagram", socialData.instagramAccount?.socialURL(host: "instagram.com")),
            ("TikTok", socialData.tiktokAccount?.socialURL(host: "tiktok.com/@")),
            ("YouTube", socialData.youtubeAccount?.socialURL(host: "youtube.com/@")),
            ("Website", URL.normalizedExternalURL(socialData.website)),
            ("Linktree", URL.normalizedExternalURL(socialData.linktree))
        ]
        .compactMap { label, url in
            guard let url else { return nil }
            return SocialLink(label: label, url: url)
        }
    }
}

private struct SocialLinkSection: View {
    let socialData: Components.Schemas.SocialData
    let openURL: (URL) -> Void

    var body: some View {
        let links = SocialLink.links(from: socialData)

        return LaughTrackCard {
            VStack(alignment: .leading, spacing: 12) {
                LaughTrackSectionHeader(
                    eyebrow: "Follow",
                    title: "Links",
                    subtitle: "Social and web destinations use the same shared CTA treatment as the rest of the app."
                )
                if links.isEmpty {
                    EmptyCard(message: "No public links are available yet.")
                } else {
                    ForEach(links) { link in
                        LaughTrackButton(link.label, systemImage: "arrow.up.right", tone: .secondary) {
                            openURL(link.url)
                        }
                    }
                }
            }
        }
    }
}

private struct SectionHeading: View {
    @Environment(\.appTheme) private var theme

    let title: String

    var body: some View {
        Text(title)
            .font(theme.laughTrackTokens.typography.cardTitle)
            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
    }
}

private struct LoadingCard: View {
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

private struct EmptyCard: View {
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

private struct ErrorCard: View {
    let title: String
    let message: String
    let retry: () async -> Void

    init(
        title: String = "Couldn’t load this section",
        message: String,
        retry: @escaping () async -> Void
    ) {
        self.title = title
        self.message = message
        self.retry = retry
    }

    var body: some View {
        LaughTrackInlineStateCard(
            tone: .error,
            title: title,
            message: message,
            actionTitle: "Try again"
        ) {
            Task {
                await retry()
            }
        }
    }
}

private struct RemoteImageView: View {
    @Environment(\.appTheme) private var theme

    let urlString: String
    let aspectRatio: CGFloat

    var body: some View {
        AsyncImage(url: URL.normalizedExternalURL(urlString)) { phase in
            switch phase {
            case .empty:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        ProgressView()
                    }
            case .success(let image):
                image
                    .resizable()
                    .scaledToFill()
            case .failure:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                    }
            @unknown default:
                Rectangle()
                    .fill(theme.laughTrackTokens.colors.surfaceElevated)
            }
        }
        .aspectRatio(aspectRatio, contentMode: .fill)
        .clipped()
    }
}

private struct InlineNavigationTitle: ViewModifier {
    func body(content: Content) -> some View {
        #if os(iOS)
        content.navigationBarTitleDisplayMode(.inline)
        #else
        content
        #endif
    }
}

private struct SearchFieldInputBehavior: ViewModifier {
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

private enum ShowFormatting {
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

private enum FavoriteFeedback {
    static func message(for name: String, isFavorite: Bool) -> String {
        isFavorite ? "Saved \(name) to favorites." : "Removed \(name) from favorites."
    }
}

private enum DemoFixtures {
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
            description: "A demo lineup stitched from the generated API schema while the live backend is offline.",
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

private extension String {
    var nonEmpty: String? {
        isEmpty ? nil : self
    }

    func socialURL(host: String) -> URL? {
        guard !isEmpty else { return nil }
        return URL(string: "https://\(host)\(self.hasPrefix("@") ? String(self.dropFirst()) : self)")
    }
}

private extension URL {
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
