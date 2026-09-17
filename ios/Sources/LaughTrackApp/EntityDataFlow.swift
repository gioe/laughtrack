import Foundation
import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

enum EntityNavigationTarget: Hashable {
    case show(Int)
    case comedian(Int)
    case club(Int)
    case podcast(Int)

    var route: AppRoute {
        switch self {
        case .show(let id):
            return .showDetail(id)
        case .comedian(let id):
            return .comedianDetail(id)
        case .club(let id):
            return .clubDetail(id)
        case .podcast(let id):
            return .podcastDetail(id)
        }
    }
}

extension TypedNavigationCoordinator where Route == AppRoute {
    /// Entity detail views cross-link in cycles (club → show → comedian →
    /// the same club …), so a plain push grows the stack without bound and
    /// the user has to tap back once per visited screen to get home.
    /// Re-opening an entity already on the stack pops back to its existing
    /// entry instead, keeping depth bounded by the set of distinct entities
    /// visited.
    func open(_ target: EntityNavigationTarget) {
        pushOrPopTo(target.route)
    }
}

enum LoadPhase<Value> {
    case idle
    case loading
    case success(Value)
    case failure(LoadFailure)
}

struct DiscoverySearchPage<Item: Sendable>: Sendable {
    let items: [Item]
    let total: Int
    let page: Int
    let filters: [Components.Schemas.Filter]
    /// Home-city filter options surfaced by comedian search; empty for other entities.
    let homeCityFilters: [Components.Schemas.HomeCityFilter]

    init(
        items: [Item],
        total: Int,
        page: Int,
        filters: [Components.Schemas.Filter],
        homeCityFilters: [Components.Schemas.HomeCityFilter] = []
    ) {
        self.items = items
        self.total = total
        self.page = page
        self.filters = filters
        self.homeCityFilters = homeCityFilters
    }

    var canLoadMore: Bool {
        items.count < total
    }
}

struct DiscoverySearchResponse<Item: Sendable>: Sendable {
    let items: [Item]
    let total: Int
    let filters: [Components.Schemas.Filter]
    /// Home-city filter options surfaced by comedian search; empty for other entities.
    let homeCityFilters: [Components.Schemas.HomeCityFilter]

    init(
        items: [Item],
        total: Int,
        filters: [Components.Schemas.Filter] = [],
        homeCityFilters: [Components.Schemas.HomeCityFilter] = []
    ) {
        self.items = items
        self.total = total
        self.filters = filters
        self.homeCityFilters = homeCityFilters
    }
}

enum ShowAvailability {
    static func isSoldOut(_ show: Components.Schemas.Show) -> Bool {
        if show.soldOut == true {
            return true
        }

        guard let tickets = show.tickets, !tickets.isEmpty else {
            return false
        }
        return tickets.allSatisfy { $0.soldOut == true }
    }

    static func availableShows(_ shows: [Components.Schemas.Show]) -> [Components.Schemas.Show] {
        shows.filter { !isSoldOut($0) }
    }
}

enum SearchResultsState: Equatable {
    case confirmed
    case updating
    case failed(LoadFailure)
    case interrupted

    var isConfirmed: Bool { self == .confirmed }
}

@MainActor
class EntitySearchModel<Query: Equatable, Item: Sendable>: ObservableObject {
    @Published private(set) var phase: LoadPhase<DiscoverySearchPage<Item>> = .idle
    @Published private(set) var isRefreshing = false
    @Published private(set) var refreshFailure: LoadFailure?
    @Published private(set) var isLoadingMore = false
    @Published private(set) var paginationFailure: LoadFailure?

    private var loadedQuery: Query?
    private var requestedQuery: Query?
    private var loadedAt: Date?
    // Fetchers may ignore cancellation. Only the current request may publish or
    // clear progress, including pagination that started before a query change.
    private var requestID = UUID()

    func resultsState(for query: Query) -> SearchResultsState {
        if requestedQuery == query {
            if isRefreshing { return .updating }
            if let refreshFailure { return .failed(refreshFailure) }
        }
        if loadedQuery == query { return .confirmed }
        return requestedQuery == query ? .interrupted : .updating
    }

    func reload(
        query: Query,
        shouldDebounce: Bool = false,
        cacheTTL: TimeInterval? = nil,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
    ) async {
        guard !Task.isCancelled else { return }
        if loadedQuery == query, case .success = phase,
           refreshFailure == nil, isLoadedValueFresh(cacheTTL: cacheTTL) {
            // A → B → A can reuse A, but B must lose ownership even if its
            // network operation is still running. Keep accumulated pages intact.
            requestID = UUID()
            requestedQuery = query
            isRefreshing = false
            isLoadingMore = false
            return
        }
        await load(page: 0, query: query, shouldDebounce: shouldDebounce, fetch: fetch, resetResults: true)
    }

    func loadMore(
        query: Query,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
    ) async {
        guard case .success(let current) = phase, current.canLoadMore,
              resultsState(for: query).isConfirmed, !isLoadingMore, !isRefreshing else { return }
        await load(page: current.page + 1, query: query, shouldDebounce: false, fetch: fetch, resetResults: false)
    }

    func loadPage(
        _ page: Int,
        query: Query,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
    ) async {
        guard page >= 0, case .success = phase,
              resultsState(for: query).isConfirmed, !isLoadingMore, !isRefreshing else { return }
        await load(page: page, query: query, shouldDebounce: false, fetch: fetch,
                   resetResults: false, appendResults: false)
    }

    var currentItems: [Item] {
        guard case .success(let current) = phase else { return [] }
        return current.items
    }

    func replaceSuccessPage(
        _ transform: (DiscoverySearchPage<Item>) -> DiscoverySearchPage<Item>
    ) {
        guard case .success(let current) = phase else { return }
        phase = .success(transform(current))
    }

    private func load(
        page: Int,
        query: Query,
        shouldDebounce: Bool,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>,
        resetResults: Bool,
        appendResults: Bool = true
    ) async {
        guard !Task.isCancelled else { return }
        let id = UUID()
        requestID = id
        let existingItems = currentItems
        paginationFailure = nil

        if resetResults {
            requestedQuery = query
            refreshFailure = nil
            isLoadingMore = false
            if case .success = phase {
                isRefreshing = true
            } else {
                isRefreshing = false
                phase = .loading
            }
        } else {
            isLoadingMore = true
        }

        defer {
            if requestID == id {
                if resetResults {
                    isRefreshing = false
                    if Task.isCancelled, case .loading = phase { phase = .idle }
                } else {
                    isLoadingMore = false
                }
            }
        }

        if resetResults, shouldDebounce {
            try? await Task.sleep(for: .milliseconds(250))
        }
        guard !Task.isCancelled, requestID == id else { return }
        let result = await fetch(page, query)
        guard !Task.isCancelled, requestID == id else { return }
        switch result {
        case .success(let response):
            loadedQuery = query
            loadedAt = Date()
            phase = .success(.init(
                items: resetResults || !appendResults ? response.items : existingItems + response.items,
                total: response.total,
                page: page,
                filters: response.filters,
                homeCityFilters: response.homeCityFilters
            ))
        case .failure(let failure):
            if case .success = phase {
                if resetResults { refreshFailure = failure }
                else { paginationFailure = failure }
            } else {
                phase = .failure(failure)
            }
        }
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval?) -> Bool {
        guard let cacheTTL else { return true }
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}

/// Detail cache entries are display seeds, not proof of freshness. Revalidate
/// every cache hit, then at most once per minute when a retained page reappears
/// or returns to the foreground. User refresh always bypasses this interval.
/// Discovery cache retention is deliberately independent of this policy.
enum DetailFreshnessPolicy {
    static let revalidationInterval: TimeInterval = 60
}

@MainActor
class EntityDetailModel<Value>: ObservableObject {
    @Published var phase: LoadPhase<Value> = .idle
    @Published private(set) var isRefreshing = false
    @Published private(set) var refreshFailure: LoadFailure?

    private var requestID = UUID()
    private var activeRequest: Task<Void, Never>?
    private var loadedAt: Date?
    private let now: () -> Date

    init(now: @escaping () -> Date = Date.init) {
        self.now = now
    }

    func loadIfNeeded(
        freshness: TimeInterval? = nil,
        using request: @escaping () async -> Result<Value, LoadFailure>
    ) async {
        switch phase {
        case .idle:
            break
        case .loading where activeRequest?.isCancelled == true:
            break
        case .success:
            guard let freshness else { return }
            if refreshFailure == nil, activeRequest?.isCancelled != true,
               let loadedAt, now().timeIntervalSince(loadedAt) < freshness { return }
        default:
            return
        }
        await refresh(using: request)
    }

    /// Concurrent user/lifecycle refreshes join the same request. A cancelled
    /// transport is replaceable immediately, even before it finishes unwinding.
    func refresh(
        using request: @escaping () async -> Result<Value, LoadFailure>
    ) async {
        guard !Task.isCancelled else { return }
        if let activeRequest, !activeRequest.isCancelled {
            await activeRequest.value
            return
        }
        await reload(using: request)
    }

    func reload(
        using request: @escaping () async -> Result<Value, LoadFailure>
    ) async {
        guard !Task.isCancelled else { return }
        let id = UUID()
        requestID = id
        activeRequest?.cancel()
        let hasContent: Bool
        if case .success = phase { hasContent = true } else { hasContent = false }
        refreshFailure = nil
        isRefreshing = hasContent
        if !hasContent { phase = .loading }

        let task = Task { @MainActor in
            let result = await request()
            guard !Task.isCancelled, requestID == id else { return }
            switch result {
            case .success(let value):
                loadedAt = now()
                phase = .success(value)
            case .failure(let failure):
                if hasContent {
                    refreshFailure = failure
                } else {
                    phase = .failure(failure)
                }
            }
        }
        activeRequest = task

        // Forward SwiftUI cancellation synchronously so returning views can
        // replace cancelled requests even when their transport ignores it.
        await withTaskCancellationHandler {
            await task.value
        } onCancel: {
            task.cancel()
        }

        guard requestID == id else { return }
        activeRequest = nil
        isRefreshing = false
        if task.isCancelled {
            loadedAt = nil
            if case .loading = phase { phase = .idle }
        }
    }
}
