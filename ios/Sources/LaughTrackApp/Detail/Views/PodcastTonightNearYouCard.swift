import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct TonightNearYouMatch: Equatable {
    let show: Components.Schemas.Show
    let hostName: String
}

struct PodcastTonightNearYouCard: View {
    let podcastID: Int
    let apiClient: Client
    let zipCode: String?

    @State private var match: TonightNearYouMatch?
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @Environment(\.appTheme) private var theme

    var body: some View {
        Group {
            if let match {
                card(for: match)
            }
        }
        .task(id: podcastID) {
            match = await TonightNearYouLoader.load(
                podcastID: podcastID,
                apiClient: apiClient,
                zipCode: zipCode
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
        zipCode: String?
    ) async -> TonightNearYouMatch? {
        async let detailTask = fetchPodcastDetail(podcastID: podcastID)
        async let feedTask = fetchHomeFeed(apiClient: apiClient, zipCode: zipCode)

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

    private static func fetchPodcastDetail(podcastID: Int) async -> PodcastDetailResponse? {
        let url = AppConfiguration.apiBaseURL
            .appendingPathComponent("api")
            .appendingPathComponent("v1")
            .appendingPathComponent("podcasts")
            .appendingPathComponent(String(podcastID))

        guard
            let (data, _) = try? await URLSession.shared.data(from: url),
            let decoded = try? JSONDecoder().decode(PodcastDetailResponse.self, from: data)
        else { return nil }
        return decoded
    }

    private static func fetchHomeFeed(
        apiClient: Client,
        zipCode: String?
    ) async -> Components.Schemas.HomeFeed? {
        let input = Operations.GetHomeFeed.Input(
            query: .init(zip: zipCode),
            headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
        )
        guard let output = try? await apiClient.getHomeFeed(input) else { return nil }
        switch output {
        case .ok(let ok):
            return (try? ok.body.json)?.data
        default:
            return nil
        }
    }
}
