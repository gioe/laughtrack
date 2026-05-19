import SwiftUI
import LaughTrackBridge

private let podcastSearchRowDesign = LaughTrackEntityRowDesign(
    artworkSize: 70,
    artworkShape: .roundedRectangle(cornerRadius: 12),
    minHeight: 86,
    titleLineLimit: 2,
    subtitleLineLimit: 1,
    metadataLineLimit: 1
)

struct PodcastSearchView: View {
    @ObservedObject var model: PodcastSearchModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var isActive = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var openDropdownID: String?

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search podcast titles",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                }

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "podcasts-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )
                }

                switch model.phase {
                case .idle, .loading:
                    PodcastsListSkeleton()
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
                                ? "No podcasts are available right now."
                                : "No podcasts matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(result.items) { podcast in
                                Button {
                                    if let target = podcast.navigationTarget {
                                        coordinator.open(target)
                                    }
                                } label: {
                                    LaughTrackEntityRow(
                                        title: podcast.title,
                                        subtitle: podcast.subtitle?.nonEmpty,
                                        systemImage: "headphones",
                                        imageURL: podcast.imageUrl,
                                        design: podcastSearchRowDesign
                                    )
                                }
                                .buttonStyle(.plain)
                                .disabled(podcast.navigationTarget == nil)
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more podcasts",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore()
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
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "podcasts-sort",
                    options: PodcastSortOption.allCases,
                    selected: $model.sort,
                    triggerLabel: { $0.title },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )
            }
        }
    }
}

