import Foundation
import LaughTrackCore

struct PodcastSearchRequest: Equatable, Sendable {
    let query: String
    let page: Int
    let limit: Int
    let sort: String

    init(query: String, page: Int = 0, limit: Int, sort: String) {
        self.query = query
        self.page = page
        self.limit = limit
        self.sort = sort
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
    private let fetcher: any PodcastSearchFetching

    override init() {
        self.fetcher = URLSessionPodcastSearchFetcher()
        super.init()
    }

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
        switch await fetcher.searchPodcasts(.init(query: query.text, page: page, limit: Self.pageSize, sort: query.sort)) {
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
            sort: sort.rawValue
        )
    }
}

struct PodcastRequestKey: Hashable, Sendable {
    let text: String
    let sort: String
}

@MainActor
final class URLSessionPodcastSearchFetcher: PodcastSearchFetching {
    fileprivate struct APIPodcast: Decodable {
        let id: Int
        let slug: String
        let title: String
        let authorName: String?
        let websiteUrl: String?
        let feedUrl: String?
        let imageUrl: String?
    }

    private struct APIResponse: Decodable {
        let data: [APIPodcast]
        let total: Int
    }

    private let baseURL: URL
    private let urlSession: URLSession

    init(
        baseURL: URL = AppConfiguration.apiBaseURL,
        urlSession: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.urlSession = urlSession
    }

    func searchPodcasts(_ request: PodcastSearchRequest) async -> Result<PodcastSearchResponse, LoadFailure> {
        guard var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/podcasts/search"), resolvingAgainstBaseURL: false) else {
            return .failure(.unexpected(status: 0, message: "LaughTrack could not build the podcast search URL."))
        }

        components.queryItems = [
            URLQueryItem(name: "q", value: request.query),
            URLQueryItem(name: "page", value: String(request.page)),
            URLQueryItem(name: "size", value: String(request.limit)),
            URLQueryItem(name: "sort", value: request.sort),
        ]

        guard let url = components.url else {
            return .failure(.unexpected(status: 0, message: "LaughTrack could not build the podcast search URL."))
        }

        do {
            let (data, response) = try await urlSession.data(from: url)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            switch status {
            case 200:
                let decoded = try JSONDecoder().decode(APIResponse.self, from: data)
                return .success(.init(
                    items: decoded.data.map(PodcastSearchResult.init(apiPodcast:)),
                    total: decoded.total
                ))
            case 400:
                return .failure(.badParams("LaughTrack could not apply that podcast search."))
            case 401:
                return .failure(.unauthorized("Sign in to load podcasts."))
            case 429:
                return .failure(.rateLimited(retryAfter: nil, message: "LaughTrack is rate-limiting podcast results right now."))
            case 500..<600:
                return .failure(.serverError(status: status, message: nil))
            default:
                return .failure(.unexpected(status: status, message: "LaughTrack returned an unexpected podcast response."))
            }
        } catch is DecodingError {
            return .failure(.decoding("LaughTrack reached the podcast search service, but could not read the response. Please try again."))
        } catch {
            return .failure(.network("LaughTrack couldn't reach the podcast search service. Check your connection and try again."))
        }
    }
}

private extension PodcastSearchResult {
    init(apiPodcast: URLSessionPodcastSearchFetcher.APIPodcast) {
        self.init(
            id: "podcast-\(apiPodcast.id)",
            title: apiPodcast.title,
            subtitle: apiPodcast.authorName,
            href: apiPodcast.websiteUrl ?? apiPodcast.feedUrl ?? "/podcast/\(apiPodcast.slug)",
            imageUrl: apiPodcast.imageUrl
        )
    }
}
