import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ComediansDiscoveryModel: EntitySearchModel<String, Components.Schemas.ComedianSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""

    func reload(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = normalizedQuery
        await super.reload(query: query, shouldDebounce: !query.isEmpty, cacheTTL: cacheTTL) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadMore(
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadMore(query: normalizedQuery) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, favorites: favorites, cache: cache, cacheTTL: cacheTTL)
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
        favorites: ComedianFavoriteStore,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.ComedianSearchItem>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.comediansSearch(query: query, page: page)
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
                    let pageResponse = DiscoverySearchResponse(
                        items: items,
                        total: response.data.count < Self.pageSize ? page * Self.pageSize + items.count : (page + 1) * Self.pageSize + 1
                    )
                    await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL)
                    return .success(pageResponse)
                case .badRequest(let badRequest):
                    return .failure(.badParams((try? badRequest.body.json.error) ?? "LaughTrack could not apply those comedian filters."))
                case .internalServerError(let serverError):
                    return .failure(.serverError(status: 500, message: (try? serverError.body.json.error)))
                case .undocumented(let status, _):
                    return .failure(classifyUndocumented(status: status, context: "comedians"))
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
                    let pageResponse = DiscoverySearchResponse(
                        items: items,
                        total: response.total
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
