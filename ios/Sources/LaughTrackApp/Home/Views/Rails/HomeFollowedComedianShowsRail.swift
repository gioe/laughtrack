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

    @EnvironmentObject private var authManager: AuthManager
    @StateObject private var model = HomeFollowedComedianShowsModel()

    private var zipCode: String? {
        nearbyPreferenceStore.preference?.zipCode
    }

    private var distanceMiles: Int? {
        nearbyPreferenceStore.preference?.distanceMiles
    }

    private var sessionDiscriminator: String? {
        guard let userId = authManager.currentUser?.userId,
              let session = authManager.currentSession else { return nil }
        return "\(userId)|\(session.signedInAt.timeIntervalSinceReferenceDate)"
    }

    var body: some View {
        Group {
            if case .success(let shows) = model.phase, !shows.isEmpty {
                HomeDiscoverRailCard(
                    variant: .spotlight,
                    eyebrow: nil,
                    title: nil,
                    subtitle: nil,
                    accessibilityIdentifier: "laughtrack.home.followed-comedian-shows-rail"
                ) {
                    HomeFeaturedShowsCarousel(
                        headline: "Because you follow them",
                        items: shows
                            .prefix(HomeDiscoverRailPlanPresentation.followedComedianShowsItemLimit)
                            .map { show in
                                HomeFeaturedShowCarouselItem(
                                    show: show,
                                    preferredHeadlinerID: HomeDiscoverRailPlanPresentation.preferredFavoriteHeadlinerID(
                                        show: show
                                    ),
                                    accessibilityIdentifier: LaughTrackViewTestID.homeFavoriteShowButton(show.id),
                                    accessibilityLabel: ShowTitlePresentation.title(for: show),
                                    timestampLabel: ShowFormatting.featuredDateTime(
                                        show.date,
                                        timezoneID: show.timezone
                                    )
                                )
                            }
                    )
                }
            }
        }
        .task(id: model.requestKey(
            for: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )) {
            guard let sessionDiscriminator else {
                model.hideForSignedOutSession()
                return
            }
            await model.refresh(
                apiClient: apiClient,
                zipCode: zipCode,
                distanceMiles: distanceMiles,
                sessionDiscriminator: sessionDiscriminator,
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

    func requestKey(
        for zipCode: String?,
        distanceMiles: Int? = nil,
        sessionDiscriminator: String? = nil
    ) -> String {
        "\(sessionDiscriminator ?? "signed-out")|\(HomeFeedRequest.requestKey(zipCode: zipCode, distanceMiles: distanceMiles))"
    }

    func refresh(
        apiClient: Client,
        zipCode: String?,
        distanceMiles: Int? = nil,
        sessionDiscriminator: String? = nil,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL,
        persistentCache: PersistentMainPageCache?,
        coalescer: HomeFeedRequestCoalescer = .shared
    ) async {
        let requestKey = requestKey(
            for: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator
        )
        if loadedRequestKey == requestKey,
           case .success = phase,
           isLoadedValueFresh(cacheTTL: cacheTTL) {
            return
        }

        phase = .loading
        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: distanceMiles,
            sessionDiscriminator: sessionDiscriminator,
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

    func hideForSignedOutSession() {
        phase = .success([])
        loadedRequestKey = nil
        loadedAt = nil
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
