import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class ClubsDiscoveryModel: EntitySearchModel<String, Components.Schemas.ClubSearchItem>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""

    func reload(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        let query = normalizedQuery
        await super.reload(query: query, shouldDebounce: !query.isEmpty, cacheTTL: cacheTTL) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
        }
    }

    func loadMore(
        apiClient: Client,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async {
        await super.loadMore(query: normalizedQuery) { page, query in
            await Self.fetchPage(page: page, query: query, apiClient: apiClient, cache: cache, cacheTTL: cacheTTL)
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
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Result<DiscoverySearchResponse<Components.Schemas.ClubSearchItem>, LoadFailure> {
        let cacheKey = LaughTrackCacheKey.clubsSearch(query: query, page: page)
        if let cached: DiscoverySearchResponse<Components.Schemas.ClubSearchItem> = await MainPageCache.get(
            cacheKey,
            from: cache
        ) {
            return .success(cached)
        }

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
                    let pageResponse = DiscoverySearchResponse(
                        items: items,
                        total: response.data.count < Self.pageSize ? page * Self.pageSize + items.count : (page + 1) * Self.pageSize + 1
                    )
                    await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL)
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
                    let pageResponse = DiscoverySearchResponse(
                        items: response.data,
                        total: response.total
                    )
                    await MainPageCache.set(pageResponse, forKey: cacheKey, in: cache, ttl: cacheTTL)
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
