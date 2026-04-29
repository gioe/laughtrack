import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct ShowsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ShowsDiscoveryModel
    var displaysSearchFields = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                LaughTrackShelfHeader(
                    eyebrow: "Shows",
                    title: "Shows nearby",
                    subtitle: "Keep filters close and results dense."
                )

                if displaysSearchFields {
                    SearchField(
                        title: "Comedian",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.comedianSearchText
                    )

                    SearchField(
                        title: "Club",
                        prompt: "Comedy Cellar, The Stand…",
                        text: $model.clubSearchText
                    )
                }

                ShowFiltersPanel(model: model)

                switch model.phase {
                case .idle, .loading:
                    LoadingCard(title: "Loading shows")
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, cache: pageCache) },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    if result.items.isEmpty {
                        EmptyCard(title: "No shows yet", message: emptyMessage)
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            SearchResultsSummary(count: result.items.count, total: result.total)
                            ShowsSearchMeta(model: model, zipCapTriggered: model.zipCapTriggered)

                            ForEach(result.items, id: \.id) { show in
                                Button {
                                    coordinator.open(.show(show.id))
                                } label: {
                                    ShowRow(show: show)
                                }
                                .buttonStyle(.plain)
                                .accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if result.canLoadMore {
                                LoadMoreButton(
                                    title: "Load more shows",
                                    isLoading: model.isLoadingMore
                                ) {
                                    await model.loadMore(apiClient: apiClient, cache: pageCache)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: model.requestKey) {
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
    }

    private var emptyMessage: String {
        if !model.comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
            !model.clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return "No shows matched this search. Try another comedian, club, or a broader date range."
        }

        if model.activeNearbyPreference != nil {
            return "No shows matched this ZIP code yet. Broaden the radius or clear location filters."
        }

        return "No shows are available right now."
    }
}

private struct ShowFiltersPanel: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        LaughTrackCard(tone: .muted, density: .compact) {
            VStack(alignment: .leading, spacing: theme.spacing.md) {
                LaughTrackShelfHeader(
                    eyebrow: "Filters",
                    title: "Tune the search",
                    subtitle: "Keep location, sort, and dates in reach."
                )

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: theme.spacing.sm) {
                        LaughTrackBrowseChip("Upcoming dates first", systemImage: "sparkles", tone: .accent)
                        LaughTrackBrowseChip("Dense result rows", systemImage: "rectangle.grid.1x2", tone: .neutral)
                        LaughTrackBrowseChip("Nearby aware", systemImage: "location.fill", tone: .neutral)
                    }
                }

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    Text("ZIP")
                        .font(laughTrack.typography.eyebrow)
                        .foregroundStyle(laughTrack.colors.textSecondary)
                        .textCase(.uppercase)

                    LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft)
                        .modifier(SearchFieldInputBehavior())
                        #if os(iOS)
                        .keyboardType(UIKeyboardType.numberPad)
                        #endif

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: theme.spacing.sm) {
                            LaughTrackButton("Use ZIP", systemImage: "location.fill", tone: .secondary, density: .compact, fullWidth: false) {
                                _ = model.applyManualZip()
                            }

                            if model.activeNearbyPreference != nil {
                                LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact, fullWidth: false) {
                                    model.clearLocation()
                                }
                            }
                        }
                    }

                    if let nearbyStatusMessage = model.nearbyStatusMessage {
                        InlineStatusMessage(message: nearbyStatusMessage)
                    } else if let activeNearbyPreference = model.activeNearbyPreference {
                        LaughTrackContextRow(
                            leading: activeNearbyPreference.source == .manual ? "Saved ZIP" : "Current location",
                            trailing: "\(activeNearbyPreference.zipCode) • \(activeNearbyPreference.distanceMiles) mi"
                        )
                    }
                }

                HStack(spacing: theme.spacing.sm) {
                    Menu {
                        Picker("Sort", selection: $model.sort) {
                            ForEach(ShowSortOption.allCases) { option in
                                Text(option.title).tag(option)
                            }
                        }
                    } label: {
                        LaughTrackBrowseChip(
                            "Sort: \(model.sort.title)",
                            systemImage: "arrow.up.arrow.down",
                            tone: .neutral
                        )
                    }

                    if model.activeNearbyPreference != nil {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: theme.spacing.sm) {
                                ForEach(ShowDistanceOption.allCases) { option in
                                    Button {
                                        model.distance = option
                                    } label: {
                                        LaughTrackBrowseChip(
                                            option.title,
                                            systemImage: "location.north.line",
                                            tone: model.distance == option ? .selected : .neutral
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }
                }

                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                    HStack {
                        Text("Dates")
                            .font(laughTrack.typography.eyebrow)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)
                        Spacer()
                        Text(model.useDateRange ? "Custom window" : "Upcoming by default")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Toggle("Use date range", isOn: $model.useDateRange)
                        .font(laughTrack.typography.body)
                        .tint(laughTrack.colors.accent)

                    if model.useDateRange {
                        VStack(spacing: theme.spacing.md) {
                            DatePicker("From", selection: $model.fromDate, displayedComponents: .date)
                            DatePicker(
                                "To",
                                selection: Binding(
                                    get: { max(model.toDate, model.fromDate) },
                                    set: { model.toDate = max($0, model.fromDate) }
                                ),
                                in: model.fromDate...,
                                displayedComponents: .date
                            )
                        }
                        .font(laughTrack.typography.body)
                    }
                }
            }
        }
    }
}

private struct ShowsSearchMeta: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel
    let zipCapTriggered: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            LaughTrackContextRow(
                leading: "Times shown in \(model.timezoneLabel)",
                trailing: "\(activeFilters.count) filters"
            )

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    ForEach(activeFilters, id: \.self) { filter in
                        LaughTrackBrowseChip(filter, tone: .neutral)
                    }
                }
            }

            if zipCapTriggered {
                LaughTrackInlineStateCard(
                    tone: .error,
                    title: "Location was broadened",
                    message: "That ZIP matched too many nearby locations. Try a tighter ZIP or clear the location filter.",
                    actionTitle: "Browse all shows"
                ) {
                    model.clearLocation()
                }
            }
        }
    }

    private var activeFilters: [String] {
        let query = model.requestKey
        var filters = ["Sort: \(query.sort.title)"]

        if let zip = query.sanitizedZip {
            filters.append("ZIP \(zip)")
            filters.append("Within \(query.distance.rawValue) mi")
        }

        if !query.comedian.isEmpty {
            filters.append("Comedian: \(query.comedian)")
        }

        if !query.club.isEmpty {
            filters.append("Club: \(query.club)")
        }

        if query.useDateRange, let from = query.fromString, let to = query.toString {
            filters.append("\(from) to \(to)")
        }

        return filters
    }
}
