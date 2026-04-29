import Foundation
import SwiftUI
import LaughTrackBridge
import LaughTrackCore

enum EntityNavigationTarget: Hashable {
    case show(Int)
    case comedian(Int)
    case club(Int)

    var route: AppRoute {
        switch self {
        case .show(let id):
            return .showDetail(id)
        case .comedian(let id):
            return .comedianDetail(id)
        case .club(let id):
            return .clubDetail(id)
        }
    }
}

extension NavigationCoordinator where Route == AppRoute {
    func open(_ target: EntityNavigationTarget) {
        push(target.route)
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

    var canLoadMore: Bool {
        items.count < total
    }
}

struct DiscoverySearchResponse<Item: Sendable>: Sendable {
    let items: [Item]
    let total: Int
}

@MainActor
class EntitySearchModel<Query: Equatable, Item: Sendable>: ObservableObject {
    @Published private(set) var phase: LoadPhase<DiscoverySearchPage<Item>> = .idle
    @Published private(set) var isLoadingMore = false
    @Published private(set) var paginationFailure: LoadFailure?

    private var loadedQuery: Query?
    private var loadingQuery: Query?
    private var loadedAt: Date?

    func reload(
        query: Query,
        shouldDebounce: Bool = false,
        cacheTTL: TimeInterval? = nil,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
    ) async {
        if loadedQuery == query, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if loadingQuery == query, case .loading = phase {
            return
        }

        await load(page: 0, query: query, shouldDebounce: shouldDebounce, fetch: fetch, resetResults: true)
    }

    func loadMore(
        query: Query,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
    ) async {
        guard case .success(let current) = phase, current.canLoadMore, !isLoadingMore else { return }
        await load(page: current.page + 1, query: query, shouldDebounce: false, fetch: fetch, resetResults: false)
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
        resetResults: Bool
    ) async {
        let existingItems = currentItems
        paginationFailure = nil

        if resetResults {
            loadingQuery = query
            phase = .loading
            if shouldDebounce {
                try? await Task.sleep(for: .milliseconds(250))
                guard !Task.isCancelled else { return }
            }
        } else {
            isLoadingMore = true
        }

        defer {
            if resetResults {
                loadingQuery = nil
            } else {
                isLoadingMore = false
            }
        }

        let result = await fetch(page, query)
        guard !Task.isCancelled else { return }
        switch result {
        case .success(let response):
            phase = .success(
                .init(
                    items: resetResults ? response.items : existingItems + response.items,
                    total: response.total,
                    page: page
                )
            )
            loadedQuery = query
            loadedAt = Date()
        case .failure(let failure):
            handleFailure(failure: failure, existingItems: existingItems, resetResults: resetResults)
        }
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval?) -> Bool {
        guard let cacheTTL else { return true }
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }

    private func handleFailure(
        failure: LoadFailure,
        existingItems: [Item],
        resetResults: Bool
    ) {
        if resetResults || existingItems.isEmpty {
            phase = .failure(failure)
        } else if case .success(let current) = phase {
            paginationFailure = failure
            phase = .success(current)
        }
    }
}

@MainActor
class EntityDetailModel<Value>: ObservableObject {
    @Published private(set) var phase: LoadPhase<Value> = .idle

    func loadIfNeeded(
        using request: @escaping () async -> Result<Value, LoadFailure>
    ) async {
        guard case .idle = phase else { return }
        await reload(using: request)
    }

    func reload(
        using request: @escaping () async -> Result<Value, LoadFailure>
    ) async {
        phase = .loading
        let result = await request()
        guard !Task.isCancelled else { return }
        switch result {
        case .success(let value):
            phase = .success(value)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }
}
