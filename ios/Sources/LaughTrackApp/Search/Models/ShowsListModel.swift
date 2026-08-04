import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum ShowActiveConstraintKind: Hashable {
    case location
    case date
    case filter(String)
    case maximumPrice
    case comedian
    case club
}

struct ShowActiveConstraint: Identifiable, Equatable {
    let kind: ShowActiveConstraintKind
    let label: String

    var id: ShowActiveConstraintKind { kind }
}

@MainActor
final class ShowsListModel: EntitySearchModel<ShowsListQuery, Components.Schemas.Show>, SearchLocationFilterModel {
    @Published var zipCodeDraft = ""
    @Published var comedianSearchText = ""
    @Published var clubSearchText = ""
    @Published var dateRange: DateRangeFilter = {
        let today = Calendar.current.startOfDay(for: Date())
        return DateRangeFilter(from: today, to: today, isActive: true)
    }()
    @Published var selectedFilterSlugs: Set<String> = []
    @Published var maximumPrice: ShowMaximumPriceOption = .any
    @Published var resultsPresentation: ShowResultsPresentation = .agenda
    @Published var distance: ShowDistanceOption = .city {
        didSet {
            guard let activeNearbyPreference, activeNearbyPreference.distanceMiles != distance.rawValue else { return }
            self.activeNearbyPreference = NearbyPreference(
                zipCode: activeNearbyPreference.zipCode,
                source: activeNearbyPreference.source,
                distanceMiles: distance.rawValue,
                city: activeNearbyPreference.city,
                state: activeNearbyPreference.state
            )
        }
    }
    @Published var sort: ShowSortOption = .earliest
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var nearbyStatusMessage: String?
    @Published private(set) var zipCapTriggered = false
    @Published private(set) var isResolvingCurrentLocation = false

    var isClubPinned: Bool {
        pinnedClubId != nil || pinnedClubName != nil
    }

    var isComedianPinned: Bool {
        pinnedComedianName != nil
    }

    var allowsLocationFiltering: Bool {
        !isClubPinned
    }

    var isShowingNationwideComedianSearch: Bool {
        allowsLocationFiltering &&
            activeNearbyPreference != nil &&
            pinnedComedianName == nil &&
            !comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var activeLocationLabel: String? {
        guard let activeNearbyPreference else { return nil }

        if let city = activeNearbyPreference.city, let state = activeNearbyPreference.state {
            return "\(city), \(state)"
        }
        if let city = activeNearbyPreference.city {
            return city
        }
        if let state = activeNearbyPreference.state {
            return state
        }
        return activeNearbyPreference.zipCode
    }

    private let nearbyLocationController: NearbyLocationController
    private let pageSize: Int
    let pinnedClubId: Int?
    let pinnedClubName: String?
    let pinnedComedianName: String?
    private var nearbyStatusCancellable: AnyCancellable?
    private var nearbyLoadingCancellable: AnyCancellable?
    private var hasSearchLocalLocationOverride = false

    init(
        nearbyLocationController: NearbyLocationController,
        pinnedClubId: Int? = nil,
        pinnedClubName: String? = nil,
        pinnedComedianName: String? = nil,
        initialUseDateRange: Bool = true,
        startsWithNearbyLocation: Bool = true,
        pageSize: Int = 20
    ) {
        self.nearbyLocationController = nearbyLocationController
        self.pageSize = max(1, pageSize)
        self.pinnedClubId = pinnedClubId
        self.pinnedClubName = pinnedClubName
        self.pinnedComedianName = pinnedComedianName
        super.init()
        dateRange.isActive = initialUseDateRange
        if startsWithNearbyLocation {
            applyNearbyPreference(nearbyLocationController.preference)
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

    var requestKey: ShowsListQuery {
        let effectiveZip = allowsLocationFiltering && !isShowingNationwideComedianSearch
            ? (activeNearbyPreference?.zipCode ?? "")
            : ""
        let effectiveDistance = NearbyPreferenceStore.validZip(from: effectiveZip) == nil
            ? ShowDistanceOption.city
            : distance

        return .init(
            comedian: pinnedComedianName ?? comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            club: pinnedClubId == nil
                ? (pinnedClubName ?? clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines))
                : "",
            clubId: pinnedClubId,
            filters: selectedFilterSlugs.sorted(),
            zip: effectiveZip,
            dateRange: dateRange,
            distance: effectiveDistance,
            maximumPrice: maximumPrice.apiValue,
            sort: sort
        )
    }

    func reload(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = requestKey
        await super.reload(query: query, shouldDebounce: query.hasActiveFilters, cacheTTL: cacheTTL) { [weak self] page, query in
            guard let self else { return .failure(.unexpected(status: 0, message: "LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadMore(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadMore(query: requestKey) { [weak self] page, query in
            guard let self else { return .failure(.unexpected(status: 0, message: "LaughTrack could not load shows right now.")) }
            return await self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadPage(
        _ page: Int,
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadPage(page, query: requestKey) { [weak self] page, query in
            guard let self else {
                return .failure(.unexpected(status: 0, message: "LaughTrack could not load shows right now."))
            }
            return await self.fetchPage(
                page: page,
                query: query,
                apiClient: apiClient,
                cache: cache,
                cacheTTL: cacheTTL
            )
        }
    }

    func pageCount(for total: Int) -> Int {
        max(1, (max(0, total) + pageSize - 1) / pageSize)
    }

    func applySearchSeedNearbyPreference(_ preference: NearbyPreference?) {
        guard let preference, allowsLocationFiltering else { return }
        hasSearchLocalLocationOverride = true
        activeNearbyPreference = preference
        zipCodeDraft = preference.zipCode
        distance = .from(distanceMiles: preference.distanceMiles)
        nearbyStatusMessage = nil
    }

    func applySearchSeed(_ seed: ShowSearchSeed?) {
        guard let seed else { return }
        if pinnedComedianName == nil {
            comedianSearchText = seed.comedian
        }
        if pinnedClubId == nil, pinnedClubName == nil {
            clubSearchText = seed.club
        }
        if let dateRange = seed.dateRange {
            self.dateRange = dateRange
        } else {
            self.dateRange.isActive = false
        }
        selectedFilterSlugs = seed.filterSlugs
        maximumPrice = seed.maximumPrice
        if let distance = seed.distance {
            self.distance = distance
        }
        resultsPresentation = seed.resultsPresentation
    }

    func makeSearchSeed() -> ShowSearchSeed {
        ShowSearchSeed(
            comedian: pinnedComedianName ?? comedianSearchText,
            club: pinnedClubName ?? clubSearchText,
            dateRange: dateRange.isActive ? dateRange : nil,
            filterSlugs: selectedFilterSlugs,
            maximumPrice: maximumPrice,
            distance: distance,
            resultsPresentation: resultsPresentation
        )
    }

    func applyDateShortcut(
        _ shortcut: String,
        now: Date = Date(),
        calendar: Calendar = .current
    ) {
        let today = calendar.startOfDay(for: now)
        switch shortcut {
        case "Tonight":
            dateRange = DateRangeFilter(
                from: today,
                to: today,
                isActive: true
            )
        case "This Weekend":
            let weekday = calendar.component(.weekday, from: today)
            let daysFromFriday: Int
            switch weekday {
            case 1:
                daysFromFriday = -2
            case 7:
                daysFromFriday = -1
            default:
                daysFromFriday = (6 - weekday + 7) % 7
            }
            let friday = calendar.date(byAdding: .day, value: daysFromFriday, to: today) ?? today
            let sunday = calendar.date(byAdding: .day, value: 2, to: friday) ?? friday
            dateRange = DateRangeFilter(from: max(today, friday), to: sunday, isActive: true)
        default:
            break
        }
        sort = .earliest
    }

    func applyDefaultNearbyPreference(_ preference: NearbyPreference?) {
        guard
            let preference,
            allowsLocationFiltering,
            !hasSearchLocalLocationOverride,
            activeNearbyPreference == nil
        else {
            return
        }

        activeNearbyPreference = preference
        zipCodeDraft = preference.zipCode
        distance = .from(distanceMiles: preference.distanceMiles)
        nearbyStatusMessage = nil
    }

    func clearLocation() {
        hasSearchLocalLocationOverride = true
        zipCodeDraft = ""
        nearbyStatusMessage = nil
        activeNearbyPreference = nil
    }

    /// Resets every user-controllable query knob — location, date range,
    /// distance, and any selected filter facets — so the next fetch returns
    /// the unfiltered list for the current pinned scope (or all shows when
    /// nothing is pinned). Useful from the empty-state action when a user
    /// believes filters are hiding results.
    func clearAllFilters() {
        clearLocation()
        dateRange.isActive = false
        distance = .city
        selectedFilterSlugs = []
        maximumPrice = .any
        sort = .earliest
        resultsPresentation = .agenda
        if pinnedComedianName == nil {
            comedianSearchText = ""
        }
        if pinnedClubId == nil, pinnedClubName == nil {
            clubSearchText = ""
        }
    }

    func activeConstraints(availableFilters: [Components.Schemas.Filter]) -> [ShowActiveConstraint] {
        var constraints: [ShowActiveConstraint] = []
        if let activeLocationLabel {
            constraints.append(.init(kind: .location, label: "\(activeLocationLabel) · \(distance.title)"))
        }
        if dateRange.isActive {
            constraints.append(.init(kind: .date, label: dateRange.pillLabel()))
        }

        let namesBySlug = Dictionary(uniqueKeysWithValues: availableFilters.map { ($0.slug, $0.name) })
        for slug in selectedFilterSlugs.sorted() {
            let fallback = ShowFormatOption(rawValue: slug)?.title ?? slug.replacingOccurrences(of: "-", with: " ").capitalized
            constraints.append(.init(kind: .filter(slug), label: namesBySlug[slug] ?? fallback))
        }
        if maximumPrice != .any {
            constraints.append(.init(kind: .maximumPrice, label: maximumPrice.title))
        }
        let comedian = comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines)
        if pinnedComedianName == nil, !comedian.isEmpty {
            constraints.append(.init(kind: .comedian, label: "Comedian: \(comedian)"))
        }
        let club = clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines)
        if pinnedClubId == nil, pinnedClubName == nil, !club.isEmpty {
            constraints.append(.init(kind: .club, label: "Club: \(club)"))
        }
        return constraints
    }

    func removeConstraint(_ kind: ShowActiveConstraintKind) {
        switch kind {
        case .location:
            clearLocation()
        case .date:
            dateRange.isActive = false
        case .filter(let slug):
            selectedFilterSlugs.remove(slug)
        case .maximumPrice:
            maximumPrice = .any
        case .comedian:
            if pinnedComedianName == nil { comedianSearchText = "" }
        case .club:
            if pinnedClubId == nil, pinnedClubName == nil { clubSearchText = "" }
        }
    }

    func applyManualZip() -> Bool {
        guard !zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            clearLocation()
            return true
        }

        guard let zipCode = NearbyPreferenceStore.validZip(from: zipCodeDraft) else {
            nearbyStatusMessage = "Enter a valid 5-digit ZIP code to search nearby shows."
            return false
        }

        hasSearchLocalLocationOverride = true
        activeNearbyPreference = NearbyPreference(
            zipCode: zipCode,
            source: .manual,
            distanceMiles: distance.rawValue
        )
        zipCodeDraft = zipCode
        nearbyStatusMessage = nil
        return true
    }

    @discardableResult
    func useCurrentLocation() async -> Bool {
        guard let preference = await nearbyLocationController.currentLocationPreference(distanceMiles: distance.rawValue) else {
            return false
        }

        activeNearbyPreference = preference
        hasSearchLocalLocationOverride = true
        zipCodeDraft = preference.zipCode
        distance = .from(distanceMiles: preference.distanceMiles)
        nearbyStatusMessage = nil
        return true
    }

    private func fetchPage(
        page: Int,
        query: ShowsListQuery,
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.Show>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.showsSearch(
            requestKey: "\(query.cacheKey)|size:\(pageSize)",
            page: page
        )
        if let cached: DiscoverySearchResponse<Components.Schemas.Show> = await MainPageCache.get(
            cacheKey,
            from: cache,
            persistentCache: nil
        ) {
            return .success(cached)
        }

        do {
            let output = try await apiClient.searchShows(
                .init(
                    query: .init(
                        zip: query.sanitizedZip,
                        from: query.fromString,
                        to: query.toString,
                        page: page,
                        size: pageSize,
                        comedian: query.comedian.nonEmpty,
                        club: query.club.nonEmpty,
                        clubId: query.clubId,
                        filters: query.filtersParam,
                        distance: query.sanitizedZip == nil ? nil : query.distance.rawValue,
                        maxPrice: query.maximumPrice,
                        sort: query.sort.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                zipCapTriggered = response.zipCapTriggered
                let availableShows = ShowAvailability.availableShows(response.data)
                let pageResponse = DiscoverySearchResponse(
                    items: availableShows,
                    total: max(0, response.total - (response.data.count - availableShows.count)),
                    filters: response.filters
                )
                await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL, persistentCache: nil)
                return .success(pageResponse)
            case .badRequest(let badRequest):
                return .failure(.badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those show filters."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(retryAfter: retryAfter, message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting show results right now."))
            case .internalServerError(let serverError):
                return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "shows"))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: "the shows search service",
                networkMessage: "LaughTrack couldn't reach the shows search service. Check your connection and try again."
            ))
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
