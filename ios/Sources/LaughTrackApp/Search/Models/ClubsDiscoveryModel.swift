import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ClubsDiscoveryModel: EntitySearchModel<PrimitiveDiscoveryQuery, Components.Schemas.ClubSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""
    @Published var selectedFilterSlugs: Set<String> = []
    @Published var sort: PrimitiveSortOption = .mostPopular

    func reload(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = requestKey
        await super.reload(query: query, shouldDebounce: !query.text.isEmpty || !query.filters.isEmpty, cacheTTL: cacheTTL) { page, query in
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
}
