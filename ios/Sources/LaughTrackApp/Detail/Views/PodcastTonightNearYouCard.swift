import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct TonightNearYouMatch: Equatable {
    let show: Components.Schemas.Show
    let hostName: String
}

private struct TonightNearYouTaskID: Hashable {
    let podcastID: Int
    let zipCode: String?
}

struct PodcastTonightNearYouCard: View {
    let podcastID: Int
    let apiClient: Client
    let zipCode: String?

    @State private var match: TonightNearYouMatch?
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        Group {
            if let match {
                card(for: match)
            }
        }
        .task(id: TonightNearYouTaskID(podcastID: podcastID, zipCode: zipCode)) {
            match = await TonightNearYouLoader.load(
                podcastID: podcastID,
                apiClient: apiClient,
                zipCode: zipCode,
                cache: pageCache
            )
        }
    }

    @ViewBuilder
    private func card(for match: TonightNearYouMatch) -> some View {
        let laughTrack = theme.laughTrackTokens
        Button {
            coordinator.push(.showDetail(match.show.id))
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "mic.fill")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .frame(width: 40, height: 40)
                    .background(laughTrack.colors.accent.opacity(0.14))
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 2) {
                    Text("Tonight near you")
                        .font(laughTrack.typography.metadata.weight(.bold))
                        .foregroundStyle(laughTrack.colors.accentStrong)
                        .textCase(.uppercase)
                    Text("\(match.hostName) at \(match.show.clubName ?? "a nearby club")")
                        .font(laughTrack.typography.body.weight(.semibold))
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                }

                Spacer(minLength: 0)

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textSecondary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(laughTrack.colors.surfaceElevated)
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(laughTrack.colors.accent.opacity(0.4), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("laughtrack.now-playing.tonight-near-you")
    }
}

enum TonightNearYouLoader {
    static func load(
        podcastID: Int,
        apiClient: Client,
        zipCode: String?,
        urlSession: URLSession = .shared,
        cache: DataCache<LaughTrackCacheKey>? = nil,
        cacheTTL: TimeInterval = MainPageCache.defaultTTL
    ) async -> TonightNearYouMatch? {
        async let detailTask = fetchPodcastDetail(podcastID: podcastID, urlSession: urlSession, cache: cache, cacheTTL: cacheTTL)
        async let feedTask = fetchHomeFeed(apiClient: apiClient, zipCode: zipCode, cache: cache, cacheTTL: cacheTTL)

        guard
            let detail = await detailTask,
            let feed = await feedTask,
            let host = detail.relatedComedians.first
        else { return nil }

        guard let show = feed.showsTonight.first(where: { show in
            show.lineup?.contains(where: { $0.id == host.id }) ?? false
        }) else { return nil }

        return TonightNearYouMatch(show: show, hostName: host.name)
    }

    private static func fetchPodcastDetail(
        podcastID: Int,
        urlSession: URLSession,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> PodcastDetailResponse? {
        let cacheKey = LaughTrackCacheKey.podcast(id: String(podcastID))
        if let cached: PodcastDetailResponse = await MainPageCache.get(
            cacheKey,
            from: cache,
            persistentCache: nil
        ) {
            return cached
        }

        let url = AppConfiguration.apiBaseURL
            .appendingPathComponent("api")
            .appendingPathComponent("v1")
            .appendingPathComponent("podcasts")
            .appendingPathComponent(String(podcastID))

        guard
            let (data, _) = try? await urlSession.data(from: url),
            let decoded = try? JSONDecoder().decode(PodcastDetailResponse.self, from: data)
        else { return nil }
        await MainPageCache.set(decoded, forKey: cacheKey, in: cache, ttl: cacheTTL, persistentCache: nil)
        return decoded
    }

    private static func fetchHomeFeed(
        apiClient: Client,
        zipCode: String?,
        cache: DataCache<LaughTrackCacheKey>?,
        cacheTTL: TimeInterval
    ) async -> Components.Schemas.HomeFeed? {
        if let cached: Components.Schemas.HomeFeed = await MainPageCache.get(
            .homeFeed(zipCode: zipCode, distanceMiles: nil),
            from: cache,
            persistentCache: nil
        ) {
            return cached
        }

        let result = await HomeFeedRequest.load(
            apiClient: apiClient,
            zipCode: zipCode,
            distanceMiles: nil,
            cache: cache,
            cacheTTL: cacheTTL,
            badParamsMessage: "LaughTrack could not load nearby shows.",
            rateLimitMessage: "LaughTrack is rate-limiting nearby shows right now.",
            undocumentedContext: "nearby shows",
            networkContext: "the home feed",
            networkMessage: "LaughTrack couldn't reach nearby shows. Check your connection and try again.",
            persistentCache: nil,
            coalescer: .shared
        )

        guard case .success(let feed) = result else { return nil }
        return feed
    }
}
