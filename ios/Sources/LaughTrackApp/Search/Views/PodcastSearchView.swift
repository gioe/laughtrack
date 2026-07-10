import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct PodcastSearchView: View {
    let apiClient: Client
    @ObservedObject var model: PodcastSearchModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var isActive = true

    @Environment(\.appTheme) private var theme
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @State private var openDropdownID: String?
    @State private var feedbackMessage: String?

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
                                PodcastSearchRow(
                                    podcast: podcast,
                                    apiClient: apiClient,
                                    feedbackMessage: $feedbackMessage
                                )
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
        .alert("Favorites", isPresented: .constant(feedbackMessage != nil), actions: {
            Button("OK") {
                feedbackMessage = nil
            }
        }, message: {
            Text(feedbackMessage ?? "")
        })
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

struct PodcastSearchRow: View {
    let podcast: PodcastSearchResult
    let apiClient: Client
    @Binding var feedbackMessage: String?

    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var podcastFavorites: PodcastFavoriteStore
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme

    private static let posterSize: CGFloat = 64
    private static let posterFrameInset: CGFloat = 5

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let numericID = Self.numericID(for: podcast)
        let isFavorite = numericID.map { podcastFavorites.value(for: $0) } ?? false
        let canOpenDetail = podcast.navigationTarget != nil

        HStack(spacing: theme.spacing.md) {
            Button {
                if canOpenDetail { openPodcastDetail() }
            } label: {
                HStack(spacing: theme.spacing.md) {
                    poster

                    Text(podcast.title)
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    if canOpenDetail {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!canOpenDetail)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(podcast.title)

            if let numericID {
                FavoriteButton(
                    isFavorite: isFavorite,
                    isPending: podcastFavorites.isPending(numericID)
                ) {
                    await toggle(podcastID: numericID, currentValue: isFavorite)
                }
            }
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.9), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
    }

    private var poster: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            posterImage
                .frame(width: Self.posterSize, height: Self.posterSize)
                .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 5, style: .continuous)
                        .stroke(Color.black.opacity(0.55), lineWidth: 1)
                )

            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(
                    laughTrack.colors.accentStrong,
                    style: StrokeStyle(
                        lineWidth: 1.5,
                        lineCap: .round,
                        lineJoin: .round,
                        dash: [0.5, 4.5]
                    )
                )
                .frame(
                    width: Self.posterSize + Self.posterFrameInset,
                    height: Self.posterSize + Self.posterFrameInset
                )
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.5), radius: 3)
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.25), radius: 7)
        }
        .frame(
            width: Self.posterSize + Self.posterFrameInset,
            height: Self.posterSize + Self.posterFrameInset
        )
    }

    @ViewBuilder
    private var posterImage: some View {
        let laughTrack = theme.laughTrackTokens
        let trimmed = podcast.imageUrl?.trimmingCharacters(in: .whitespacesAndNewlines)

        if let raw = trimmed, let url = URL.normalizedExternalURL(raw) {
            CachedAsyncImage(url: url) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Rectangle()
                    .fill(laughTrack.colors.surfaceMuted)
                    .overlay {
                        ProgressView()
                            .tint(laughTrack.colors.accent)
                    }
            } error: { _ in
                posterFallback
            }
        } else {
            posterFallback
        }
    }

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: ArtworkFallbackKind.podcast.systemImage)
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    private func openPodcastDetail() {
        guard let target = podcast.navigationTarget else { return }
        coordinator.open(target)
    }

    private func toggle(podcastID: Int, currentValue: Bool) async {
        let result = await podcastFavorites.toggle(
            podcastID: podcastID,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )
        switch result {
        case .updated(let next):
            feedbackMessage = FavoriteFeedback.message(for: podcast.title, isFavorite: next)
        case .signInRequired:
            loginModalPresenter.present()
        case .failure(let message):
            feedbackMessage = message
        }
    }

    static func numericID(for podcast: PodcastSearchResult) -> Int? {
        guard podcast.id.hasPrefix("podcast-"),
              let value = Int(podcast.id.dropFirst("podcast-".count))
        else { return nil }
        return value
    }
}
