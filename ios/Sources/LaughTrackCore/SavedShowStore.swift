import Combine
import Foundation
import LaughTrackAPIClient
import LaughTrackBridge

@MainActor
public final class SavedShowStore: ObservableObject {
    public enum Period: String, CaseIterable, Sendable {
        case upcoming
        case past

        fileprivate var apiValue: Operations.GetSavedShows.Input.Query.PeriodPayload {
            switch self {
            case .upcoming: return .upcoming
            case .past: return .past
            }
        }
    }

    public struct Page: Equatable, Sendable {
        public let shows: [Components.Schemas.Show]
        public let total: Int
        public let page: Int
        public let size: Int
        public let totalPages: Int

        fileprivate init(_ response: Components.Schemas.SavedShowListResponse) {
            shows = response.data
            total = response.total
            page = response.page
            size = response.size
            totalPages = response.totalPages
        }
    }

    public enum LoadPhase: Equatable, Sendable {
        case idle
        case loading
        case loaded
        case empty
        case failure(LoadFailure)
    }

    public enum MutationResult: Equatable, Sendable {
        case updated(Bool)
        case queued(Bool)
        case signInRequired(String)
        case failure(String)
    }

    @Published private var values: [Int: Bool] = [:]
    @Published private var pending: Set<Int> = []
    @Published public private(set) var upcomingPage: Page?
    @Published public private(set) var pastPage: Page?
    @Published public private(set) var upcomingPhase: LoadPhase = .idle
    @Published public private(set) var pastPhase: LoadPhase = .idle
    @Published public private(set) var stateFailure: LoadFailure?

    private let cache: DataCache<LaughTrackCacheKey>
    private let persistentCache: PersistentMainPageCache
    private let offlineQueue: OfflineOperationQueue<LaughTrackOfflineOperation>
    private let cacheTTL: TimeInterval
    private let replayDelaysNanoseconds: [UInt64]
    private var activeAccountId: String?
    private var accountCacheKeys: Set<LaughTrackCacheKey> = []
    private var authLifecycleCancellable: AnyCancellable?
    private var replayTask: Task<Void, Never>?
    private var loadingAccounts: [Period: String] = [:]

    init(
        cache: DataCache<LaughTrackCacheKey>,
        persistentCache: PersistentMainPageCache,
        offlineQueue: OfflineOperationQueue<LaughTrackOfflineOperation>,
        cacheTTL: TimeInterval = 15 * 60,
        replayDelaysNanoseconds: [UInt64] = [
            2_000_000_000,
            4_000_000_000,
            8_000_000_000,
            16_000_000_000,
        ]
    ) {
        self.cache = cache
        self.persistentCache = persistentCache
        self.offlineQueue = offlineQueue
        self.cacheTTL = cacheTTL
        self.replayDelaysNanoseconds = replayDelaysNanoseconds
    }

    public func value(for showId: Int, fallback: Bool? = nil) -> Bool {
        values[showId] ?? fallback ?? false
    }

    public func storedValue(for showId: Int) -> Bool? {
        values[showId]
    }

    public func isPending(_ showId: Int) -> Bool {
        pending.contains(showId)
    }

    public func resetAccountState() async {
        let priorAccountId = activeAccountId
        let keys = accountCacheKeys
        replayTask?.cancel()
        replayTask = nil
        clearPublishedState()

        for key in keys {
            await cache.remove(forKey: key)
        }
        if let priorAccountId {
            await persistentCache.removeSavedShows(accountId: priorAccountId)
        }
        await offlineQueue.clearAll()
    }

    public func bindAuthLifecycle(
        authManager: AuthManager,
        apiClient: Client
    ) {
        authLifecycleCancellable = authManager.$currentUser
            .map(\.?.userId)
            .removeDuplicates()
            .sink { [weak self, weak authManager] accountId in
                Task { @MainActor [weak self, weak authManager] in
                    guard let self, let authManager else { return }
                    await self.handleAccountChange(
                        accountId,
                        apiClient: apiClient,
                        authManager: authManager
                    )
                }
            }
    }

    public func loadState(
        showId: Int,
        apiClient: Client,
        authManager: AuthManager,
        force: Bool = false
    ) async {
        guard let accountId = await prepareAccount(authManager: authManager) else {
            return
        }

        let key = LaughTrackCacheKey.savedShowState(
            accountId: accountId,
            showId: showId
        )
        accountCacheKeys.insert(key)
        if !force, let cached: Bool = await cache.get(forKey: key) {
            guard activeAccountId == accountId else { return }
            values[showId] = cached
            stateFailure = nil
            return
        }

        do {
            let output = try await apiClient.getSavedShowState(
                path: .init(showId: showId)
            )
            guard activeAccountId == accountId else { return }
            switch output {
            case .ok(let ok):
                let isSaved = try ok.body.json.data.isSaved
                values[showId] = isSaved
                stateFailure = nil
                await cache.set(isSaved, forKey: key, ttl: cacheTTL)
            case .badRequest(let response):
                stateFailure = .badParams(
                    (try? response.body.json.error) ?? "That show identifier is invalid."
                )
            case .unauthorized(let response):
                stateFailure = .unauthorized(
                    (try? response.body.json.error) ?? "Sign in to load saved-show state."
                )
            case .notFound(let response):
                stateFailure = .unexpected(
                    status: 404,
                    message: (try? response.body.json.error) ?? "That show could not be found."
                )
            case .unprocessableContent(let response):
                stateFailure = .unexpected(
                    status: 422,
                    message: (try? response.body.json.error)
                )
            case .tooManyRequests:
                stateFailure = .rateLimited(retryAfter: nil, message: nil)
            case .internalServerError(let response):
                stateFailure = .serverError(
                    status: 500,
                    message: (try? response.body.json.error)
                )
            case .undocumented(let status, _):
                stateFailure = classifyUndocumented(
                    status: status,
                    context: "saved-show state",
                    notFoundMessage: "That show could not be found."
                )
            }
        } catch {
            guard !Task.isCancelled else { return }
            guard activeAccountId == accountId else { return }
            stateFailure = classifyRequestError(
                error,
                context: "saved-show state",
                networkMessage: "LaughTrack couldn’t reach the saved-shows service."
            )
        }
    }

    public func loadSavedShows(
        period: Period,
        page: Int = 1,
        size: Int = 20,
        apiClient: Client,
        authManager: AuthManager,
        force: Bool = false
    ) async {
        guard let accountId = await prepareAccount(authManager: authManager) else {
            return
        }

        if page > 1,
           let current = currentPage(for: period),
           page > current.totalPages {
            return
        }
        guard loadingAccounts[period] == nil else { return }
        loadingAccounts[period] = accountId
        defer {
            if loadingAccounts[period] == accountId {
                loadingAccounts[period] = nil
            }
        }

        setPhase(.loading, for: period)
        let key = LaughTrackCacheKey.savedShows(
            accountId: accountId,
            period: period.rawValue,
            page: page,
            size: size
        )
        accountCacheKeys.insert(key)

        if !force {
            if let cached: Components.Schemas.SavedShowListResponse = await cache.get(forKey: key) {
                guard activeAccountId == accountId else { return }
                apply(cached, period: period)
                return
            }
            if let cached = await persistentCache.getSavedShows(
                accountId: accountId,
                period: period.rawValue,
                page: page,
                size: size
            ) {
                guard activeAccountId == accountId else { return }
                await cache.set(cached, forKey: key, ttl: cacheTTL)
                guard activeAccountId == accountId else { return }
                apply(cached, period: period)
                return
            }
        }

        do {
            let output = try await apiClient.getSavedShows(
                query: .init(
                    period: period.apiValue,
                    page: page,
                    size: size
                )
            )
            guard activeAccountId == accountId else { return }
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                apply(response, period: period)
                await cache.set(response, forKey: key, ttl: cacheTTL)
                await persistentCache.setSavedShows(
                    response,
                    accountId: accountId,
                    period: period.rawValue,
                    page: page,
                    size: size,
                    ttl: cacheTTL
                )
            case .badRequest(let response):
                setPhase(
                    .failure(.badParams(
                        (try? response.body.json.error) ?? "That saved-show page is invalid."
                    )),
                    for: period
                )
            case .unauthorized(let response):
                setPhase(
                    .failure(.unauthorized(
                        (try? response.body.json.error) ?? "Sign in to load saved shows."
                    )),
                    for: period
                )
            case .unprocessableContent(let response):
                setPhase(
                    .failure(.unexpected(
                        status: 422,
                        message: (try? response.body.json.error)
                    )),
                    for: period
                )
            case .tooManyRequests:
                setPhase(.failure(.rateLimited(retryAfter: nil, message: nil)), for: period)
            case .internalServerError(let response):
                setPhase(
                    .failure(.serverError(
                        status: 500,
                        message: (try? response.body.json.error)
                    )),
                    for: period
                )
            case .undocumented(let status, _):
                setPhase(
                    .failure(classifyUndocumented(status: status, context: "saved shows")),
                    for: period
                )
            }
        } catch {
            guard !Task.isCancelled else { return }
            guard activeAccountId == accountId else { return }
            setPhase(
                .failure(classifyRequestError(
                    error,
                    context: "saved shows",
                    networkMessage: "LaughTrack couldn’t reach the saved-shows service."
                )),
                for: period
            )
        }
    }

    public func loadNextSavedShowsPage(
        period: Period,
        size: Int = 20,
        apiClient: Client,
        authManager: AuthManager,
        force: Bool = false
    ) async {
        guard let current = currentPage(for: period) else {
            await loadSavedShows(
                period: period,
                size: size,
                apiClient: apiClient,
                authManager: authManager,
                force: force
            )
            return
        }
        guard current.page < current.totalPages else { return }

        await loadSavedShows(
            period: period,
            page: current.page + 1,
            size: current.size,
            apiClient: apiClient,
            authManager: authManager,
            force: force
        )
    }

    public func setSaved(
        showId: Int,
        isSaved: Bool,
        show: Components.Schemas.Show? = nil,
        apiClient: Client,
        authManager: AuthManager
    ) async -> MutationResult {
        guard let accountId = await prepareAccount(authManager: authManager) else {
            return .signInRequired("Sign in to save shows.")
        }

        let previousValue = values[showId] ?? false
        let previousUpcoming = upcomingPage
        let previousPast = pastPage
        values[showId] = isSaved
        applyOptimisticCollectionChange(showId: showId, isSaved: isSaved, show: show)
        pending.insert(showId)
        let stateKey = LaughTrackCacheKey.savedShowState(
            accountId: accountId,
            showId: showId
        )
        accountCacheKeys.insert(stateKey)
        await cache.set(isSaved, forKey: stateKey, ttl: cacheTTL)
        defer {
            if activeAccountId == accountId {
                pending.remove(showId)
            }
        }
        await invalidateCollectionCaches(accountId: accountId)

        let operationType = LaughTrackOfflineOperation.setSavedShow(
            accountId: accountId,
            showId: showId
        )
        let queuedIntentExists = await offlineQueue.pendingOperationsList.contains {
            $0.type == operationType
        }

        if queuedIntentExists {
            return await replaceQueuedIntentAndReplay(
                accountId: accountId,
                showId: showId,
                isSaved: isSaved,
                previousValue: previousValue,
                previousUpcoming: previousUpcoming,
                previousPast: previousPast,
                apiClient: apiClient,
                authManager: authManager
            )
        }

        do {
            let serverValue = try await performMutation(
                showId: showId,
                isSaved: isSaved,
                apiClient: apiClient
            )
            guard activeAccountId == accountId else {
                return .signInRequired("The active account changed before that update completed.")
            }
            values[showId] = serverValue
            if serverValue != isSaved {
                upcomingPage = previousUpcoming
                pastPage = previousPast
            }
            await cache.set(serverValue, forKey: stateKey, ttl: cacheTTL)
            return .updated(serverValue)
        } catch MutationFailure.signInRequired(let message) {
            guard activeAccountId == accountId else {
                return .signInRequired("The active account changed before that update completed.")
            }
            await rollback(
                showId: showId,
                value: previousValue,
                upcoming: previousUpcoming,
                past: previousPast,
                accountId: accountId
            )
            return .signInRequired(message)
        } catch MutationFailure.permanent(let message) {
            guard activeAccountId == accountId else {
                return .signInRequired("The active account changed before that update completed.")
            }
            await rollback(
                showId: showId,
                value: previousValue,
                upcoming: previousUpcoming,
                past: previousPast,
                accountId: accountId
            )
            return .failure(message)
        } catch {
            guard activeAccountId == accountId else {
                return .signInRequired("The active account changed before that update completed.")
            }
            do {
                let replay = try await enqueueAndReplay(
                    accountId: accountId,
                    showId: showId,
                    isSaved: isSaved
                )
                guard activeAccountId == accountId else {
                    return .signInRequired("The active account changed before that update completed.")
                }
                if replay.failed {
                    await rollback(
                        showId: showId,
                        value: previousValue,
                        upcoming: previousUpcoming,
                        past: previousPast,
                        accountId: accountId
                    )
                    return .failure("LaughTrack couldn’t replay that saved-show change.")
                }
                return replay.pending ? .queued(isSaved) : .updated(isSaved)
            } catch {
                await rollback(
                    showId: showId,
                    value: previousValue,
                    upcoming: previousUpcoming,
                    past: previousPast,
                    accountId: accountId
                )
                return .failure("LaughTrack couldn’t save that change for retry.")
            }
        }
    }

    private enum MutationFailure: Error {
        case signInRequired(String)
        case permanent(String)
        case transient
    }

    private struct ReplayResult {
        let pending: Bool
        let failed: Bool
    }

    private func replaceQueuedIntentAndReplay(
        accountId: String,
        showId: Int,
        isSaved: Bool,
        previousValue: Bool,
        previousUpcoming: Page?,
        previousPast: Page?,
        apiClient: Client,
        authManager: AuthManager
    ) async -> MutationResult {
        do {
            let replay = try await enqueueAndReplay(
                accountId: accountId,
                showId: showId,
                isSaved: isSaved
            )
            guard activeAccountId == accountId,
                  authManager.currentUser?.userId == accountId
            else {
                return .signInRequired("The active account changed before that update completed.")
            }
            if replay.failed {
                await rollback(
                    showId: showId,
                    value: previousValue,
                    upcoming: previousUpcoming,
                    past: previousPast,
                    accountId: accountId
                )
                return .failure("LaughTrack couldn’t replay that saved-show change.")
            }
            if replay.pending {
                return .queued(isSaved)
            }

            await loadState(
                showId: showId,
                apiClient: apiClient,
                authManager: authManager,
                force: true
            )
            return .updated(values[showId] ?? isSaved)
        } catch {
            guard activeAccountId == accountId else {
                return .signInRequired("The active account changed before that update completed.")
            }
            await rollback(
                showId: showId,
                value: previousValue,
                upcoming: previousUpcoming,
                past: previousPast,
                accountId: accountId
            )
            return .failure("LaughTrack couldn’t save that change for retry.")
        }
    }

    private func enqueueAndReplay(
        accountId: String,
        showId: Int,
        isSaved: Bool
    ) async throws -> ReplayResult {
        let operationType = LaughTrackOfflineOperation.setSavedShow(
            accountId: accountId,
            showId: showId
        )
        let priorFailedIds = Set((await offlineQueue.failedOperations).map(\.id))
        let payload = try JSONEncoder().encode(
            SavedShowMutationPayload(
                accountId: accountId,
                showId: showId,
                isSaved: isSaved
            )
        )
        try await offlineQueue.enqueue(type: operationType, payload: payload)
        await offlineQueue.syncPendingOperations()

        let pending = await offlineQueue.pendingOperationsList.contains {
            $0.type == operationType
        }
        let failed = await offlineQueue.failedOperations.contains {
            !priorFailedIds.contains($0.id) && $0.type == operationType
        }
        if pending {
            scheduleReplay(accountId: accountId)
        }
        return ReplayResult(pending: pending, failed: failed)
    }

    private func scheduleReplay(accountId: String) {
        guard replayTask == nil else { return }
        replayTask = Task { @MainActor [weak self] in
            guard let self else { return }
            defer { replayTask = nil }

            for delay in replayDelaysNanoseconds {
                do {
                    try await Task.sleep(nanoseconds: delay)
                } catch {
                    return
                }
                guard activeAccountId == accountId else { return }

                await offlineQueue.syncPendingOperations()
                let hasPendingSavedShows = await offlineQueue.pendingOperationsList.contains {
                    guard case .setSavedShow(let operationAccountId, _) = $0.type else {
                        return false
                    }
                    return operationAccountId == accountId
                }
                if !hasPendingSavedShows {
                    return
                }
            }
        }
    }

    private func handleAccountChange(
        _ accountId: String?,
        apiClient: Client,
        authManager: AuthManager
    ) async {
        if activeAccountId != nil, activeAccountId != accountId {
            await resetAccountState()
        }
        guard let accountId else { return }

        activeAccountId = accountId
        await offlineQueue.syncPendingOperations()

        guard activeAccountId == accountId,
              authManager.currentUser?.userId == accountId
        else { return }
        let hasPendingSavedShows = await offlineQueue.pendingOperationsList.contains {
            guard case .setSavedShow(let operationAccountId, _) = $0.type else {
                return false
            }
            return operationAccountId == accountId
        }
        if hasPendingSavedShows {
            scheduleReplay(accountId: accountId)
        }
        await reconcileReplayFailures(
            accountId: accountId,
            apiClient: apiClient,
            authManager: authManager
        )
    }

    func handleReplayFailure(
        accountId: String,
        showId: Int,
        apiClient: Client,
        authManager: AuthManager
    ) async {
        guard activeAccountId == accountId,
              authManager.currentUser?.userId == accountId
        else { return }

        await loadState(
            showId: showId,
            apiClient: apiClient,
            authManager: authManager,
            force: true
        )
        await reloadVisibleCollections(apiClient: apiClient, authManager: authManager)
    }

    private func reconcileReplayFailures(
        accountId: String,
        apiClient: Client,
        authManager: AuthManager
    ) async {
        let showIds: Set<Int> = Set(
            (await offlineQueue.failedOperations).compactMap { operation -> Int? in
            guard case .setSavedShow(let operationAccountId, let showId) = operation.type,
                  operationAccountId == accountId
            else { return nil }
            return showId
            }
        )
        for showId in showIds {
            await handleReplayFailure(
                accountId: accountId,
                showId: showId,
                apiClient: apiClient,
                authManager: authManager
            )
        }
    }

    private func reloadVisibleCollections(
        apiClient: Client,
        authManager: AuthManager
    ) async {
        if let page = upcomingPage {
            let lastLoadedPage = page.page
            await loadSavedShows(
                period: .upcoming,
                size: page.size,
                apiClient: apiClient,
                authManager: authManager,
                force: true
            )
            let targetPage = min(lastLoadedPage, upcomingPage?.totalPages ?? 0)
            while upcomingPage?.page ?? 0 < targetPage {
                let pageBeforeLoad = upcomingPage?.page ?? 0
                await loadNextSavedShowsPage(
                    period: .upcoming,
                    apiClient: apiClient,
                    authManager: authManager,
                    force: true
                )
                guard upcomingPage?.page ?? 0 > pageBeforeLoad else { break }
            }
        }
        if let page = pastPage {
            let lastLoadedPage = page.page
            await loadSavedShows(
                period: .past,
                size: page.size,
                apiClient: apiClient,
                authManager: authManager,
                force: true
            )
            let targetPage = min(lastLoadedPage, pastPage?.totalPages ?? 0)
            while pastPage?.page ?? 0 < targetPage {
                let pageBeforeLoad = pastPage?.page ?? 0
                await loadNextSavedShowsPage(
                    period: .past,
                    apiClient: apiClient,
                    authManager: authManager,
                    force: true
                )
                guard pastPage?.page ?? 0 > pageBeforeLoad else { break }
            }
        }
    }

    private func performMutation(
        showId: Int,
        isSaved: Bool,
        apiClient: Client
    ) async throws -> Bool {
        if isSaved {
            let output = try await apiClient.saveShow(path: .init(showId: showId))
            switch output {
            case .ok(let ok):
                return try ok.body.json.data.isSaved
            case .unauthorized(let response):
                throw MutationFailure.signInRequired(
                    (try? response.body.json.error) ?? "Your session expired. Sign in again."
                )
            case .badRequest(let response):
                throw MutationFailure.permanent(
                    (try? response.body.json.error) ?? "That show cannot be saved."
                )
            case .notFound(let response):
                throw MutationFailure.permanent(
                    (try? response.body.json.error) ?? "That show could not be found."
                )
            case .conflict(let response):
                throw MutationFailure.permanent(
                    (try? response.body.json.error) ?? "Past shows cannot be newly saved."
                )
            case .unprocessableContent(let response):
                throw MutationFailure.permanent(
                    (try? response.body.json.error) ?? "Your account needs to sign in again."
                )
            case .tooManyRequests, .internalServerError:
                throw MutationFailure.transient
            case .undocumented(let status, _):
                if status == 429 || status >= 500 {
                    throw MutationFailure.transient
                }
                throw MutationFailure.permanent(
                    "LaughTrack returned an unexpected response (\(status))."
                )
            }
        }

        let output = try await apiClient.unsaveShow(path: .init(showId: showId))
        switch output {
        case .ok(let ok):
            return try ok.body.json.data.isSaved
        case .unauthorized(let response):
            throw MutationFailure.signInRequired(
                (try? response.body.json.error) ?? "Your session expired. Sign in again."
            )
        case .badRequest(let response):
            throw MutationFailure.permanent(
                (try? response.body.json.error) ?? "That saved show is invalid."
            )
        case .unprocessableContent(let response):
            throw MutationFailure.permanent(
                (try? response.body.json.error) ?? "Your account needs to sign in again."
            )
        case .tooManyRequests, .internalServerError:
            throw MutationFailure.transient
        case .undocumented(let status, _):
            if status == 429 || status >= 500 {
                throw MutationFailure.transient
            }
            throw MutationFailure.permanent(
                "LaughTrack returned an unexpected response (\(status))."
            )
        }
    }

    private func prepareAccount(authManager: AuthManager) async -> String? {
        guard authManager.currentSession != nil,
              let accountId = authManager.currentUser?.userId
        else {
            await resetAccountState()
            return nil
        }
        if let activeAccountId, activeAccountId != accountId {
            await resetAccountState()
        }
        activeAccountId = accountId
        return accountId
    }

    private func clearPublishedState() {
        values = [:]
        pending = []
        upcomingPage = nil
        pastPage = nil
        upcomingPhase = .idle
        pastPhase = .idle
        stateFailure = nil
        activeAccountId = nil
        accountCacheKeys = []
        loadingAccounts = [:]
    }

    private func apply(
        _ response: Components.Schemas.SavedShowListResponse,
        period: Period
    ) {
        let responseShows = response.data.filter { values[$0.id] != false }
        let shows: [Components.Schemas.Show]
        if response.page > 1, let current = currentPage(for: period) {
            var showsById: [Int: Components.Schemas.Show] = [:]
            current.shows
                .filter { values[$0.id] != false }
                .forEach { showsById[$0.id] = $0 }
            responseShows.forEach { showsById[$0.id] = $0 }
            shows = sorted(Array(showsById.values), for: period)
        } else {
            shows = sorted(responseShows, for: period)
        }
        let page = Page(.init(
            data: shows,
            total: max(
                shows.count,
                response.total - (response.data.count - responseShows.count)
            ),
            page: response.page,
            size: response.size,
            totalPages: response.totalPages
        ))
        responseShows.forEach { values[$0.id] = true }
        switch period {
        case .upcoming:
            upcomingPage = page
            upcomingPhase = shows.isEmpty ? .empty : .loaded
        case .past:
            pastPage = page
            pastPhase = shows.isEmpty ? .empty : .loaded
        }
    }

    private func currentPage(for period: Period) -> Page? {
        switch period {
        case .upcoming: upcomingPage
        case .past: pastPage
        }
    }

    private func sorted(
        _ shows: [Components.Schemas.Show],
        for period: Period
    ) -> [Components.Schemas.Show] {
        shows.sorted { lhs, rhs in
            if lhs.date == rhs.date {
                return period == .upcoming ? lhs.id < rhs.id : lhs.id > rhs.id
            }
            return period == .upcoming ? lhs.date < rhs.date : lhs.date > rhs.date
        }
    }

    private func setPhase(_ phase: LoadPhase, for period: Period) {
        switch period {
        case .upcoming: upcomingPhase = phase
        case .past: pastPhase = phase
        }
    }

    private func applyOptimisticCollectionChange(
        showId: Int,
        isSaved: Bool,
        show: Components.Schemas.Show?
    ) {
        if !isSaved {
            upcomingPage = removing(showId: showId, from: upcomingPage)
            pastPage = removing(showId: showId, from: pastPage)
            return
        }

        guard let show else { return }
        let period: Period = show.date >= Date() ? .upcoming : .past
        switch period {
        case .upcoming:
            guard let page = upcomingPage else { return }
            upcomingPage = inserting(show, into: page, period: period)
        case .past:
            guard let page = pastPage else { return }
            pastPage = inserting(show, into: page, period: period)
        }
    }

    private func inserting(
        _ show: Components.Schemas.Show,
        into page: Page,
        period: Period
    ) -> Page {
        guard !page.shows.contains(where: { $0.id == show.id }) else {
            return page
        }

        let total = page.total + 1
        let sorted = sorted(page.shows + [show], for: period)
        let loadedCapacity = max(page.shows.count, page.page * page.size)
        return replacing(
            page: page,
            shows: Array(sorted.prefix(loadedCapacity)),
            total: total
        )
    }

    private func removing(showId: Int, from page: Page?) -> Page? {
        guard let page, page.shows.contains(where: { $0.id == showId }) else {
            return page
        }
        return replacing(
            page: page,
            shows: page.shows.filter { $0.id != showId },
            total: max(0, page.total - 1)
        )
    }

    private func replacing(page: Page, shows: [Components.Schemas.Show], total: Int) -> Page {
        Page(.init(
            data: shows,
            total: total,
            page: page.page,
            size: page.size,
            totalPages: max(1, Int(ceil(Double(total) / Double(max(1, page.size)))))
        ))
    }

    private func rollback(
        showId: Int,
        value: Bool,
        upcoming: Page?,
        past: Page?,
        accountId: String
    ) async {
        values[showId] = value
        upcomingPage = upcoming
        pastPage = past
        let key = LaughTrackCacheKey.savedShowState(
            accountId: accountId,
            showId: showId
        )
        accountCacheKeys.insert(key)
        await cache.set(value, forKey: key, ttl: cacheTTL)
    }

    private func invalidateCollectionCaches(accountId: String) async {
        let keys = accountCacheKeys.filter { key in
            if case .savedShows(let cachedAccountId, _, _, _) = key {
                return cachedAccountId == accountId
            }
            return false
        }
        for key in keys {
            await cache.remove(forKey: key)
            accountCacheKeys.remove(key)
        }
        await persistentCache.removeSavedShows(accountId: accountId)
    }
}
