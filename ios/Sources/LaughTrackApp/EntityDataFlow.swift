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
    case failure(LoadFailure)
}

enum LoadFailure: Error, Equatable, Sendable {
    case network(String)
    case badParams(String)
    case unauthorized(String)
    case serverError(status: Int, message: String?)
    case unexpected(status: Int, message: String?)

    var message: String {
        switch self {
        case .network(let message):
            return message
        case .badParams(let message):
            return "\(message) (HTTP 400)"
        case .unauthorized(let message):
            return "\(message) (HTTP 401)"
        case .serverError(let status, let message):
            let base = message ?? "LaughTrack hit a server error. Please retry in a moment."
            return "\(base) (HTTP \(status))"
        case .unexpected(let status, let message):
            let base = message ?? "LaughTrack returned an unexpected response."
            return status > 0 ? "\(base) (HTTP \(status))" : base
        }
    }

    var defaultTitle: String {
        switch self {
        case .network:
            return "No connection"
        case .badParams:
            return "Check these filters"
        case .unauthorized:
            return "Sign in required"
        case .serverError:
            return "Server hiccup"
        case .unexpected:
            return "Unexpected response"
        }
    }
}

func classifyUndocumented(status: Int, context: String) -> LoadFailure {
    switch status {
    case 401:
        return .unauthorized("Sign in to load \(context).")
    case 400:
        return .badParams("LaughTrack could not apply those \(context) filters.")
    case 500..<600:
        return .serverError(status: status, message: nil)
    default:
        return .unexpected(status: status, message: "LaughTrack returned an unexpected \(context) response.")
    }
}

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
    @Published private(set) var paginationFailure: LoadFailure?

    private var loadedQuery: Query?
    private var loadingQuery: Query?

    func reload(
        query: Query,
        shouldDebounce: Bool = false,
        fetch: @escaping (_ page: Int, _ query: Query) async -> Result<DiscoverySearchResponse<Item>, LoadFailure>
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

        switch await fetch(page, query) {
        case .success(let response):
            phase = .success(
                .init(
                    items: resetResults ? response.items : existingItems + response.items,
                    total: response.total,
                    page: page
                )
            )
            loadedQuery = query
        case .failure(let failure):
            handleFailure(failure: failure, existingItems: existingItems, resetResults: resetResults)
        }
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
        switch await request() {
        case .success(let value):
            phase = .success(value)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }
}
