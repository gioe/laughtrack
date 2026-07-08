import SwiftUI
#if os(iOS)
import UIKit
#endif
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
final class HomeFavoriteShowsModel: ObservableObject {
    private static let maxFavoriteQueries = 5
    private static let showsPerFavorite = 3

    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func refresh(
        apiClient: Client,
        favoriteComedians: [Components.Schemas.ComedianSearchItem],
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?
    ) async {
        let requestKey = Self.requestKey(for: favoriteComedians)
        guard !requestKey.isEmpty else {
            loadedRequestKey = nil
            loadedAt = nil
            phase = .idle
            return
        }
        if loadedRequestKey == requestKey, case .success = phase, isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedShows: [Components.Schemas.Show] = await MainPageCache.get(
            .favoriteShows(requestKey: requestKey),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(shows: cachedShows, requestKey: requestKey)
            return
        }

        phase = .loading

        var showsByID: [Int: Components.Schemas.Show] = [:]

        for comedian in favoriteComedians.prefix(Self.maxFavoriteQueries) {
            do {
                let output = try await apiClient.searchShows(
                    .init(
                        query: .init(
                            from: ShowFormatting.apiDate(Date()),
                            page: 0,
                            size: Self.showsPerFavorite,
                            comedian: comedian.name,
                            sort: ShowSortOption.earliest.rawValue
                        ),
                        headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                    )
                )

                guard case .ok(let ok) = output else { continue }
                let response = try ok.body.json
                for show in response.data where Self.show(show, matches: comedian) {
                    showsByID[show.id] = show
                }
            } catch {
                guard !Task.isCancelled else { return }
                continue
            }
        }

        let shows = ShowAvailability.availableShows(Array(showsByID.values)).sorted { $0.date < $1.date }
        await MainPageCache.set(
            shows,
            forKey: .favoriteShows(requestKey: requestKey),
            in: cache,
            ttl: cacheTTL,
            persistentCache: persistentCache
        )
        apply(shows: shows, requestKey: requestKey)
    }

    private func apply(shows: [Components.Schemas.Show], requestKey: String) {
        phase = .success(shows)
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    static func requestKey(for favoriteComedians: [Components.Schemas.ComedianSearchItem]) -> String {
        favoriteComedians.map(\.uuid).joined(separator: "|")
    }

    static func show(
        _ show: Components.Schemas.Show,
        matches favorite: Components.Schemas.ComedianSearchItem
    ) -> Bool {
        guard let lineup = show.lineup, !lineup.isEmpty else { return true }
        return lineup.contains { comedian in
            comedian.uuid == favorite.uuid ||
                comedian.id == favorite.id ||
                comedian.name.localizedCaseInsensitiveCompare(favorite.name) == .orderedSame
        }
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
