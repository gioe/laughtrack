import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ClubsDiscoveryModel: EntitySearchModel<ClubsDiscoveryQuery, Components.Schemas.ClubSearchItem>, SearchRootQueryReceivable, SearchLocationFilterModel {
    private static let pageSize = 20

    @Published var searchText = ""
    @Published var selectedFilterSlugs: Set<String> = []
    @Published var sort: ClubSortOption = .mostActive
    @Published var includeEmpty: Bool = false
    @Published var zipCodeDraft = ""
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
    @Published private(set) var activeNearbyPreference: NearbyPreference?
    @Published private(set) var nearbyStatusMessage: String?
    @Published private(set) var isResolvingCurrentLocation = false

    private let nearbyLocationController: NearbyLocationController
    private var nearbyStatusCancellable: AnyCancellable?
    private var nearbyLoadingCancellable: AnyCancellable?
    private var hasSearchLocalLocationOverride = false

    init(nearbyLocationController: NearbyLocationController) {
        self.nearbyLocationController = nearbyLocationController
        super.init()
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

    func reload(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = requestKey
        await super.reload(
            query: query,
            shouldDebounce: !query.text.isEmpty || !query.filters.isEmpty,
            cacheTTL: cacheTTL
        ) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadMore(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadMore(query: requestKey) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    var requestKey: ClubsDiscoveryQuery {
        ClubsDiscoveryQuery(
            text: searchText.trimmingCharacters(in: .whitespacesAndNewlines),
            filters: selectedFilterSlugs.sorted(),
            sort: sort.rawValue,
            includeEmpty: includeEmpty,
            zip: activeNearbyPreference?.zipCode ?? "",
            distance: distance
        )
    }

    func applySearchSeedNearbyPreference(_ preference: NearbyPreference?) {
        guard let preference else { return }
        hasSearchLocalLocationOverride = true
        applyNearbyPreference(preference)
        nearbyStatusMessage = nil
    }

    func applyDefaultNearbyPreference(_ preference: NearbyPreference?) {
        guard
            let preference,
            !hasSearchLocalLocationOverride,
            activeNearbyPreference == nil
        else {
            return
        }

        applyNearbyPreference(preference)
        nearbyStatusMessage = nil
    }

    func clearLocation() {
        hasSearchLocalLocationOverride = true
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
            nearbyStatusMessage = "Enter a valid 5-digit ZIP code to search nearby clubs."
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
        guard let preference = await nearbyLocationController.currentLocationPreference(
            distanceMiles: distance.rawValue
        ) else {
            return false
        }

        hasSearchLocalLocationOverride = true
        applyNearbyPreference(preference)
        nearbyStatusMessage = nil
        return true
    }

    private static func fetchPage(
        page: Int,
        query: ClubsDiscoveryQuery,
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.ClubSearchItem>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.clubsSearch(query: query.cacheKey, page: page)
        if let cached: DiscoverySearchResponse<Components.Schemas.ClubSearchItem> = await MainPageCache.get(
            cacheKey,
            from: cache,
            persistentCache: nil
        ) {
            return .success(cached)
        }

        do {
            let output = try await apiClient.searchClubs(
                .init(
                    query: .init(
                        club: query.text.nonEmpty,
                        sort: query.sort,
                        filters: query.filtersParam,
                        page: page,
                        size: Self.pageSize,
                        includeEmpty: query.includeEmpty ? "true" : nil,
                        zip: query.sanitizedZip,
                        distance: query.sanitizedZip == nil ? nil : query.distance.rawValue
                    ),
                    headers: .init(xTimezone: TimeZone.current.identifier)
                )
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let pageResponse = DiscoverySearchResponse(
                    items: response.data,
                    total: response.total,
                    filters: response.filters
                )
                await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL, persistentCache: nil)
                return .success(pageResponse)
            case .badRequest(let badRequest):
                return .failure(.badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those club filters."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(retryAfter: retryAfter, message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting club results right now."))
            case .internalServerError(let serverError):
                return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "clubs"))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: "the clubs service",
                networkMessage: "LaughTrack couldn't reach the clubs service. Check your connection and try again."
            ))
        }
    }

    private func applyNearbyPreference(_ preference: NearbyPreference?) {
        activeNearbyPreference = preference

        if let preference {
            zipCodeDraft = preference.zipCode
            distance = .from(distanceMiles: preference.distanceMiles)
        } else {
            zipCodeDraft = ""
            distance = .city
        }
    }
}
