import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

/// A fail-soft personalized Discover rail. The home-feed endpoint already
/// returns the complete, bounded set for this shelf, so there is deliberately
/// no "See all" action that would imply Search can reproduce the same query.
struct HomeFollowedComedianShowsRail: View {
    let apiClient: Client
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore
    let cache: DataCache<LaughTrackCacheKey>
    let persistentCache: PersistentMainPageCache

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme
    @StateObject private var model = HomeFollowedComedianShowsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    var body: some View {
        Group {
            if case .success(let shows) = model.phase, !shows.isEmpty {
                HomeDiscoverRailCard(
                    variant: .scheduleBoard,
                    eyebrow: "Your lineup",
                    title: "Shows from comedians you follow",
                    subtitle: nil,
                    accessibilityIdentifier: "laughtrack.home.followed-comedian-shows-rail"
                ) {
                    VStack(spacing: theme.spacing.sm) {
                        ForEach(shows, id: \.id) { show in
                            Button {
                                coordinator.open(.show(show.id))
                            } label: {
                                ShowRow(show: show, presentation: .compactTicket)
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier(LaughTrackViewTestID.homeFavoriteShowButton(show.id))
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey(for: zipCode, distanceMiles: distanceMiles)) {
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                cache: cache,
                persistentCache: persistentCache
            )
        }
    }
}

@MainActor
final class HomeFollowedComedianShowsModel: ObservableObject {
    @Published private(set) var phase: LoadPhase<[Components.Schemas.Show]> = .idle

    private var loadedRequestKey: String?
    private var loadedAt: Date?

    func requestKey(for zipCode: String?, distanceMiles: Int? = nil) -> String {
        HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles)
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(for: zipCode, distanceMiles: distanceMiles)
        if loadedRequestKey == requestKey,
           case .success = phase,
           isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        if let cachedFeed: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: distanceMiles),
            from: cache,
            persistentCache: persistentCache
        ) {
            apply(feed: cachedFeed, requestKey: requestKey)
            return
        }

        phase = .loading
        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load followed-comedian shows.",
            rateLimitMessage: "LaughTrack is rate-limiting followed-comedian shows right now.",
            undocumentedContext: "followed-comedian shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach the home feed. Check your connection and try again.",
            persistentCache: persistentCache,
            coalescer: coalescer
        )
        guard !Task.isCancelled else { return }

        switch result {
        case .success(let feed):
            apply(feed: feed, requestKey: requestKey)
        case .failure(let failure):
            phase = .failure(failure)
        }
    }

    static func railItems(from feed: Components.Schemas.HomeFeed) -> [Components.Schemas.Show] {
        feed.followedComedianShows
    }

    private func apply(feed: Components.Schemas.HomeFeed, requestKey: String) {
        phase = .success(Self.railItems(from: feed))
        loadedRequestKey = requestKey
        loadedAt = Date()
    }

    private func isLoadedValueFresh(cacheTTL: TimeInterval) -> Bool {
        guard let loadedAt else { return false }
        return Date().timeIntervalSince(loadedAt) < cacheTTL
    }
}
