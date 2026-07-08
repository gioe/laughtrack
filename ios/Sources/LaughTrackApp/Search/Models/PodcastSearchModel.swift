import Foundation
import LaughTrackAPIClient
import LaughTrackCore

struct PodcastSearchRequest: Equatable, Sendable {
    let query: String
    let page: Int
    let limit: Int
    let sort: String
    let includeEmpty: Bool

    init(query: String, page: Int = 0, limit: Int, sort: String, includeEmpty: Bool = false) {
        self.query = query
        self.page = page
        self.limit = limit
        self.sort = sort
        self.includeEmpty = includeEmpty
    }
}

struct PodcastSearchResponse: Equatable, Sendable {
    let items: [PodcastSearchResult]
    let total: Int
}

struct PodcastSearchResult: Codable, Equatable, Identifiable, Sendable {
    let id: String
    let title: String
    let subtitle: String?
    let href: String
    let imageUrl: String?

    var navigationTarget: EntityNavigationTarget? {
        guard id.hasPrefix("podcast-"),
              let numericID = Int(id.dropFirst("podcast-".count))
        else { return nil }

        return .podcast(numericID)
    }
}

@MainActor
protocol PodcastSearchFetching {
    func searchPodcasts(_ request: PodcastSearchRequest) async -> Result<PodcastSearchResponse, LoadFailure>
}

@MainActor
final class PodcastSearchModel: EntitySearchModel<PodcastRequestKey, PodcastSearchResult>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""
    @Published var sort: PodcastSortOption = .mostEpisodes
    @Published var includeEmpty: Bool = false
    private let fetcher: any PodcastSearchFetching

    init(fetcher: any PodcastSearchFetching) {
        self.fetcher = fetcher
        super.init()
    }

    func reload() async {
        let key = requestKey
        await super.reload(query: key, shouldDebounce: !key.text.isEmpty, fetch: fetchPage)
    }

    func loadMore() async {
        await super.loadMore(query: requestKey, fetch: fetchPage)
    }

    private func fetchPage(page: Int, query: PodcastRequestKey) async -> Result<DiscoverySearchResponse<PodcastSearchResult>, LoadFailure> {
        switch await fetcher.searchPodcasts(.init(query: query.text, page: page, limit: Self.pageSize, sort: query.sort, includeEmpty: query.includeEmpty)) {
        case .success(let response):
            return .success(.init(items: response.items, total: response.total))
        case .failure(let failure):
            return .failure(failure)
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    var requestKey: PodcastRequestKey {
        PodcastRequestKey(
            text: searchText.trimmingCharacters(in: .whitespacesAndNewlines),
            sort: sort.rawValue,
            includeEmpty: includeEmpty
        )
    }
}

struct PodcastRequestKey: Hashable, Sendable {
    let text: String
    let sort: String
    let includeEmpty: Bool
}

/// Routes podcast search through the generated OpenAPI client (and thus
/// TokenRefreshMiddleware), replacing the former hand-rolled URLSession fetcher
/// that skipped auto-refresh on 401 (TASK-3631). LoadFailure classification
/// reuses the shared `classifyUndocumented`/`classifyRequestError` helpers, so
/// a 401 still surfaces "Sign in to load podcasts."
@MainActor
final class APIPodcastSearchFetcher: PodcastSearchFetching {
    private let apiClient: Client

    init(apiClient: Client) {
        self.apiClient = apiClient
    }

    func searchPodcasts(_ request: PodcastSearchRequest) async -> Result<PodcastSearchResponse, LoadFailure> {
        do {
            let output = try await apiClient.searchPodcasts(
                .init(query: .init(
                    q: request.query,
                    sort: request.sort,
                    page: request.page,
                    size: request.limit,
                    includeEmpty: request.includeEmpty ? "true" : nil
                ))
            )

            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                return .success(.init(
                    items: response.data.map(PodcastSearchResult.init(apiPodcast:)),
                    total: response.total
                ))
            case .tooManyRequests:
                return .failure(classifyUndocumented(status: 429, context: "podcasts"))
            case .internalServerError:
                return .failure(classifyUndocumented(status: 500, context: "podcasts"))
            case .undocumented(let status, _):
                return .failure(classifyUndocumented(status: status, context: "podcasts"))
            }
        } catch {
            return .failure(classifyRequestError(
                error,
                context: "the podcast search service",
                networkMessage: "LaughTrack couldn't reach the podcast search service. Check your connection and try again."
            ))
        }
    }
}

private extension PodcastSearchResult {
    init(apiPodcast: Components.Schemas.PodcastSearchItem) {
        self.init(
            id: "podcast-\(apiPodcast.id)",
            title: apiPodcast.title,
            subtitle: apiPodcast.authorName,
            href: apiPodcast.websiteUrl ?? apiPodcast.feedUrl ?? "/podcast/\(apiPodcast.slug)",
            imageUrl: apiPodcast.imageUrl
        )
    }
}
