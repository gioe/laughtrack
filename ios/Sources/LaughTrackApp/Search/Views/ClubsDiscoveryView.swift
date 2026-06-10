import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ClubsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ClubsDiscoveryModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var displaysSearchInput = true
    var isActive = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var isFilterEditorPresented = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search club names",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                } else if displaysSearchInput {
                    SearchField(
                        title: "Club name",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.searchText
                    )
                }

                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                    PillDropdownTrigger(
                        id: "clubs-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )

                    PillSheetTrigger(
                        title: model.selectedFilterSlugs.count > 0 ? filterCountTitle : "Filters",
                        systemImage: "line.3.horizontal.decrease",
                        isActive: model.selectedFilterSlugs.count > 0,
                        accessibilityLabel: "Filter results"
                    ) {
                        isFilterEditorPresented = true
                    }
                }

                switch model.phase {
                case .idle, .loading:
                    ClubsListSkeleton()
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, cache: pageCache) },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(
                            title: "No clubs yet",
                            message: model.searchText.isEmpty
                                ? "No clubs are available right now."
                                : "No clubs matched \"\(model.searchText)\"."
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)

                            ForEach(Array(result.items.enumerated()), id: \.offset) { _, club in
                                Button {
                                    if let id = club.id {
                                        coordinator.open(.club(id))
                                    }
                                } label: {
                                    ClubRow(club: club)
                                }
                                .buttonStyle(.plain)
                                .disabled(club.id == nil)
                                .accessibilityIdentifier(club.id.map(LaughTrackViewTestID.clubsSearchResultButton) ?? "laughtrack.clubs-search.result-missing-id")
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more clubs",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient, cache: pageCache)
                                }
                            }
                        }
                    }
                }
            }
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .sheet(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: currentFilters,
                total: currentTotal,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented
            )
            .presentationDetents([.medium, .large])
        }
        .accessibilityIdentifier(LaughTrackViewTestID.clubsSearchScreen)
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "clubs-sort",
                    options: ClubSortOption.allCases,
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

    private var currentFilters: [Components.Schemas.Filter] {
        guard case .success(let result) = model.phase else { return [] }
        return result.filters
    }

    private var currentTotal: Int {
        guard case .success(let result) = model.phase else { return 0 }
        return result.total
    }

    private var filterCountTitle: String {
        let count = model.selectedFilterSlugs.count
        return "\(count) filter\(count == 1 ? "" : "s")"
    }
}

struct ClubRow: View {
    let club: Components.Schemas.ClubSearchItem

    @Environment(\.appTheme) private var theme

    private static let posterSize: CGFloat = 64
    private static let posterFrameInset: CGFloat = 5

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        HStack(spacing: theme.spacing.md) {
            poster

            VStack(alignment: .leading, spacing: 4) {
                Text(Self.title(for: club))
                    .font(laughTrack.typography.cardTitle)
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text(Self.subtitle(for: club))
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textSecondary)
        }
        .padding(laughTrack.browseDensity.compactCardPadding)
        .background(laughTrack.colors.surfaceElevated)
        .overlay(
            RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                .stroke(laughTrack.colors.borderStrong.opacity(0.9), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
        .shadowStyle(laughTrack.shadows.card)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(Self.title(for: club)), \(Self.subtitle(for: club))")
    }

    private var poster: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            posterImage
                .frame(width: Self.posterSize, height: Self.posterSize)
                .clipShape(Circle())
                .overlay(
                    Circle()
                        .stroke(Color.black.opacity(0.55), lineWidth: 1)
                )

            Circle()
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
        let trimmed = club.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines)

        if let url = URL.normalizedExternalURL(trimmed) {
            CachedAsyncImage(url: url) { image in
                image
                    .resizable()
                    .scaledToFit()
                    .frame(width: Self.posterSize, height: Self.posterSize)
                    .background(laughTrack.colors.surfaceMuted)
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
                Image(systemName: "building.2.fill")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }

    static func title(for club: Components.Schemas.ClubSearchItem) -> String {
        club.name ?? "Unknown club"
    }

    static func subtitle(for club: Components.Schemas.ClubSearchItem) -> String {
        [club.city, club.state].compactMap { $0 }.joined(separator: ", ").nonEmpty ?? club.address ?? "Address unavailable"
    }

    /// Retained for `ClubRowTests` (the metadata helper used to drive a
    /// "N active comedians • N shows" line in the row that has since been
    /// removed in favor of a cleaner subtitle-only treatment).
    static func metadata(for club: Components.Schemas.ClubSearchItem) -> [String] {
        [
            club.activeComedianCount.map { "\($0) active comedians" },
            club.showCount.map { "\($0) shows" },
        ].compactMap { $0 }
    }
}
