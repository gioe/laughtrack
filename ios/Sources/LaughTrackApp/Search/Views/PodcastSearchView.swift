import SwiftUI
import LaughTrackBridge

struct PodcastSearchView: View {
    @ObservedObject var model: PodcastSearchModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var isActive = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Podcasts",
                    title: "Podcasts in rotation",
                    subtitle: "Search comedy podcasts without changing your nearby show filters."
                )

                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search podcast titles",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    ComediansListSkeleton()
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload() },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No podcasts yet",
                            message: model.searchText.isEmpty
                                ? "Search for a podcast title or host."
                                : "No podcasts matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(result.items) { podcast in
                                PodcastAppearanceRow(
                                    item: podcast.playbackItem,
                                    isCurrent: false
                                ) {
                                    if let target = podcast.navigationTarget {
                                        coordinator.open(target)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload()
        }
    }
}

private extension PodcastSearchResult {
    var playbackItem: PodcastPlaybackItem {
        PodcastPlaybackItem(
            id: numericID ?? 0,
            podcastID: numericID,
            episodeTitle: title,
            podcastName: subtitle?.nonEmpty ?? "Podcast",
            podcastImageURL: imageUrl,
            displayRole: "Podcast",
            audioURL: nil,
            episodeURL: URL.normalizedExternalURL(href),
            failedAudioURL: nil
        )
    }

    var numericID: Int? {
        guard id.hasPrefix("podcast-") else { return nil }
        return Int(id.dropFirst("podcast-".count))
    }
}
