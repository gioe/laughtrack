import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ComediansDiscoveryModel: EntitySearchModel<PrimitiveDiscoveryQuery, Components.Schemas.ComedianSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""
    @Published var selectedFilterSlugs: Set<String> = []
    @Published var sort: PrimitiveSortOption = .mostPopular

    func reload(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = requestKey
        await super.reload(query: query, shouldDebounce: !query.text.isEmpty || !query.filters.isEmpty, cacheTTL: cacheTTL) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadMore(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadMore(query: requestKey) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    var requestKey: PrimitiveDiscoveryQuery {
        PrimitiveDiscoveryQuery(
            text: searchText.trimmingCharacters(in: .whitespacesAndNewlines),
            filters: selectedFilterSlugs.sorted(),
            sort: sort
        )
    }

    private static func fetchPage(
        page: Int,
        query: PrimitiveDiscoveryQuery,
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.ComedianSearchItem>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.comediansSearch(query: query.cacheKey, page: page)
        if let cached: DiscoverySearchResponse<Components.Schemas.ComedianSearchItem> = await MainPageCache.get(
            cacheKey,
            from: cache
        ) {
            cached.items.forEach { comedian in
                favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
            }
            return .success(cached)
        }

        do {
            let output = try await apiClient.searchComedians(
                .init(
                    query: .init(
                        comedian: query.text.nonEmpty,
                        sort: query.sort.rawValue,
                        filters: query.filtersParam,
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
                let pageResponse = DiscoverySearchResponse(
                    items: items,
                    total: response.total,
                    filters: response.filters
                )
                await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL)
                return .success(pageResponse)
            case .badRequest(let badRequest):
                return .failure(.badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those comedian filters."))
            case .tooManyRequests(let tooManyRequests):
                let retryAfter = tooManyRequests.headers.retryAfter.map(TimeInterval.init)
                return .failure(.rateLimited(retryAfter: retryAfter, message: (try? tooManyRequests.body.json.error) ?? "LaughTrack is rate-limiting comedian results right now."))
            case .internalServerError(let serverError):
                return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "comedians"))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: "the comedians service",
                networkMessage: "LaughTrack couldn't reach the comedians service. Check your connection and try again."
            ))
        }
    }
}
