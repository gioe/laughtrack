import Foundation
import LaughTrackCore

struct PodcastSearchRequest: Equatable, Sendable {
    let query: String
    let limit: Int
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
final class PodcastSearchModel: EntitySearchModel<String, PodcastSearchResult>, SearchRootQueryReceivable {
    private static let pageSize = 20

    @Published var searchText = ""
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
        let query = requestKey
        await super.reload(query: query, shouldDebounce: !query.isEmpty) { _, query in
            switch await self.fetcher.searchPodcasts(.init(query: query, limit: Self.pageSize)) {
            case .success(let response):
                return .success(.init(items: response.items, total: response.total))
            case .failure(let failure):
                return .failure(failure)
            }
        }
    }

    func applySearchRootQuery(_ query: String) {
        searchText = query
    }

    var requestKey: String {
        searchText.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

@MainActor
private final class URLSessionPodcastSearchFetcher: PodcastSearchFetching {
    private struct APIResponse: Decodable {
        let data: [PodcastSearchResult]
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
        guard var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/search"), resolvingAgainstBaseURL: false) else {
            return .failure(.unexpected(status: 0, message: "LaughTrack could not build the podcast search URL."))
        }

        components.queryItems = [
            URLQueryItem(name: "q", value: request.query),
            URLQueryItem(name: "type", value: "podcast"),
            URLQueryItem(name: "limit", value: String(request.limit)),
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
                return .success(.init(items: decoded.data, total: decoded.total))
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
