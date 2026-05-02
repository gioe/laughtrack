import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ShowsDiscoveryModel: EntitySearchModel<ShowsDiscoveryQuery, Components.Schemas.Show>, SearchRootQueryReceivable {
    enum NearbyShortcutSelectionResult: Equatable {
        case resolved
        case cleared
        case failed
    }

    private static let pageSize = 10

    @Published var zipCodeDraft = ""
    @Published var comedianSearchText = ""
    @Published var clubSearchText = ""
    @Published var useDateRange = true
    @Published var selectedFilterSlugs: Set<String> = []
    @Published var fromDate = Calendar.current.startOfDay(for: Date())
    @Published var toDate = Calendar.current.startOfDay(for: Date())
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
        pinnedClubName != nil
    }

    var allowsLocationFiltering: Bool {
        !isClubPinned
    }

    var dateRangeChipTitle: String {
        guard useDateRange else { return "Any date" }

        let calendar = Calendar.current
        let normalizedFrom = calendar.startOfDay(for: fromDate)
        let normalizedTo = calendar.startOfDay(for: max(toDate, fromDate))
        let today = calendar.startOfDay(for: Date())

        if normalizedFrom == today, normalizedTo == today {
            return "Today"
        }

        if normalizedFrom == normalizedTo {
            return Self.shortDateFormatter.string(from: normalizedFrom)
        }

        return "\(Self.shortDateFormatter.string(from: normalizedFrom)) - \(Self.shortDateFormatter.string(from: normalizedTo))"
    }

    private let nearbyLocationController: NearbyLocationController
    private let pinnedClubName: String?
    private var nearbyStatusCancellable: AnyCancellable?
    private var nearbyLoadingCancellable: AnyCancellable?

    private static let shortDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.setLocalizedDateFormatFromTemplate("MMM d")
        return formatter
    }()
    init(
        nearbyLocationController: NearbyLocationController,
        pinnedClubName: String? = nil,
        initialUseDateRange: Bool = true
    ) {
        self.nearbyLocationController = nearbyLocationController
        self.pinnedClubName = pinnedClubName
        super.init()
        useDateRange = initialUseDateRange
        applyNearbyPreference(nearbyLocationController.preference)
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
            club: pinnedClubName ?? clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines),
            filters: selectedFilterSlugs.sorted(),
            zip: allowsLocationFiltering ? (activeNearbyPreference?.zipCode ?? "") : "",
            useDateRange: useDateRange,
            from: fromDate,
            to: trimmedTo,
            distance: distance,
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

    func applySearchRootQuery(_ query: String) {
        // The unified root currently treats show search as a comedian-name query.
        // Venue-name discovery remains explicit in the Clubs pivot.
        comedianSearchText = query
        clubSearchText = pinnedClubName ?? ""
    }

    func applySearchSeedNearbyPreference(_ preference: NearbyPreference?) {
        guard let preference, allowsLocationFiltering else { return }
        activeNearbyPreference = preference
        zipCodeDraft = preference.zipCode
        distance = .from(distanceMiles: preference.distanceMiles)
        nearbyStatusMessage = nil
    }

    func clearLocation() {
        zipCodeDraft = ""
        nearbyStatusMessage = nil
        activeNearbyPreference = nil
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
        zipCodeDraft = preference.zipCode
        distance = .from(distanceMiles: preference.distanceMiles)
        nearbyStatusMessage = nil
        return true
    }

    @discardableResult
    func selectNearbyShortcut() async -> NearbyShortcutSelectionResult {
        if activeNearbyPreference != nil {
            clearLocation()
            return .cleared
        }

        return await useCurrentLocation() ? .resolved : .failed
    }

    private func fetchPage(
        page: Int,
        query: ShowsDiscoveryQuery,
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.Show>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.showsSearch(requestKey: query.cacheKey, page: page)
        if let cached: DiscoverySearchResponse<Components.Schemas.Show> = await MainPageCache.get(
            cacheKey,
            from: cache
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
                        size: Self.pageSize,
                        comedian: query.comedian.nonEmpty,
                        club: query.club.nonEmpty,
                        filters: query.filtersParam,
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
                let pageResponse = DiscoverySearchResponse(
                    items: response.data,
                    total: response.total,
                    filters: response.filters
                )
                await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL)
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
