import Foundation
import SwiftUI
import LaughTrackBridge

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
    case failure(String)
}

struct LoadFailure: Error, Equatable, Sendable, ExpressibleByStringLiteral, CustomStringConvertible {
    let message: String

    init(_ message: String) {
        self.message = message
    }

    init(stringLiteral value: StringLiteralType) {
        self.message = value
    }

    var description: String { message }
}

typealias LoadResult<Value> = Result<Value, LoadFailure>

struct DiscoverySearchPage<Item> {
    let items: [Item]
    let total: Int
    let page: Int

    var canLoadMore: Bool {
        items.count < total
    }
}

struct DiscoverySearchResponse<Item> {
    let items: [Item]
    let total: Int
}

@MainActor
class EntitySearchModel<Query: Equatable, Item>: ObservableObject {
    @Published private(set) var phase: LoadPhase<DiscoverySearchPage<Item>> = .idle
    @Published private(set) var isLoadingMore = false
    @Published private(set) var paginationMessage: String?

    private var loadedQuery: Query?
    private var loadingQuery: Query?

    func reload(
        query: Query,
        shouldDebounce: Bool = false,
        fetch: @escaping (_ page: Int, _ query: Query) async throws -> LoadResult<DiscoverySearchResponse<Item>>
    ) async {
        if loadedQuery == query, case .success = phase {
            return
        }

        if loadingQuery == query, case .loading = phase {
            return
        }

        await load(page: 0, query: query, shouldDebounce: shouldDebounce, fetch: fetch, resetResults: true)
    }

    func loadMore(
        query: Query,
        fetch: @escaping (_ page: Int, _ query: Query) async throws -> LoadResult<DiscoverySearchResponse<Item>>
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
        fetch: @escaping (_ page: Int, _ query: Query) async throws -> LoadResult<DiscoverySearchResponse<Item>>,
        resetResults: Bool
    ) async {
        let existingItems = currentItems
        paginationMessage = nil

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

        do {
            let result = try await fetch(page, query)
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
            case .failure(let error):
                handleFailure(message: error.message, existingItems: existingItems, resetResults: resetResults)
            }
        } catch {
            guard !Task.isCancelled else { return }
            handleFailure(
                message: "LaughTrack could not reach this service. Check your connection and try again.",
                existingItems: existingItems,
                resetResults: resetResults
            )
        }
    }

    private func handleFailure(
        message: String,
        existingItems: [Item],
        resetResults: Bool
    ) {
        if resetResults || existingItems.isEmpty {
            phase = .failure(message)
        } else if case .success(let current) = phase {
            paginationMessage = message
            phase = .success(current)
        }
    }
}

@MainActor
class EntityDetailModel<Value>: ObservableObject {
    @Published private(set) var phase: LoadPhase<Value> = .idle

    func loadIfNeeded(
        using request: @escaping () async -> LoadResult<Value>
    ) async {
        guard case .idle = phase else { return }
        await reload(using: request)
    }

    func reload(
        using request: @escaping () async -> LoadResult<Value>
    ) async {
        phase = .loading
        phase = await request().fold(
            onSuccess: { .success($0) },
            onFailure: { .failure($0.message) }
        )
    }
}

private extension Result {
    func fold<T>(
        onSuccess: (Success) -> T,
        onFailure: (Failure) -> T
    ) -> T {
        switch self {
        case .success(let success):
            return onSuccess(success)
        case .failure(let failure):
            return onFailure(failure)
        }
    }
}
