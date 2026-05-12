import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

struct ShowsListView: View {
    let apiClient: Client
    @ObservedObject var model: ShowsListModel
    var unifiedSearchText: Binding<String>?
    var unifiedSearchPrompt: String?
    var displaysSearchFields = true
    var isActive = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var isZipEditorPresented = false
    @State private var isFilterEditorPresented = false
    @State private var isDateEditorPresented = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    var body: some View {
        LaughTrackCard(density: .compact) {
            VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                if let unifiedSearchText {
                    SearchField(
                        title: "Search",
                        prompt: unifiedSearchPrompt ?? "Search nearby comedy",
                        text: unifiedSearchText,
                        showsTitle: false
                    )
                } else if displaysSearchFields {
                    if !model.isComedianPinned {
                        SearchField(
                            title: "Comedian",
                            prompt: "Mark Normand, Atsuko Okatsuka…",
                            text: $model.comedianSearchText
                        )
                    }

                    if !model.isClubPinned {
                        SearchField(
                            title: "Club",
                            prompt: "Comedy Cellar, The Stand…",
                            text: $model.clubSearchText
                        )
                    }
                }

                ShowFiltersPanel(
                    model: model,
                    filters: currentFilters,
                    total: currentTotal,
                    isZipEditorPresented: $isZipEditorPresented,
                    isFilterEditorPresented: $isFilterEditorPresented,
                    isDateEditorPresented: $isDateEditorPresented,
                    openDropdownID: $openDropdownID
                )

                switch model.phase {
                case .idle, .loading:
                    ShowsListSkeleton()
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

                            ForEach(result.items, id: \.id) { show in
                                Button {
                                    coordinator.open(.show(show.id))
                                } label: {
                                    ShowRow(
                                        show: show,
                                        nearbyRadiusMiles: model.activeNearbyPreference.map { Double($0.distanceMiles) }
                                    )
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
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .sheet(isPresented: $isZipEditorPresented) {
            LocationFilterSheet(model: model, isPresented: $isZipEditorPresented)
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
        .sheet(isPresented: $isDateEditorPresented) {
            ShowsDateRangeSheet(model: model, apiClient: apiClient, isPresented: $isDateEditorPresented)
        }
        .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
        .overlayPreferenceValue(PillDropdownAnchorKey.self) { anchors in
            GeometryReader { proxy in
                PillDropdownOverlay(
                    id: "shows-distance",
                    options: ShowDistanceOption.allCases,
                    selected: $model.distance,
                    triggerLabel: { "Distance \($0.title)" },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )

                PillDropdownOverlay(
                    id: "shows-sort",
                    options: ShowSortOption.allCases,
                    selected: $model.sort,
                    triggerLabel: { "Sort \($0.title)" },
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

    @ObservedObject var model: ShowsListModel
    let filters: [Components.Schemas.Filter]
    let total: Int
    @Binding var isZipEditorPresented: Bool
    @Binding var isFilterEditorPresented: Bool
    @Binding var isDateEditorPresented: Bool
    @Binding var openDropdownID: String?

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.md) {
            SearchToolbar {
                EmptyView()
            } filterChipSet: {
                if model.allowsLocationFiltering {
                    PillDropdownTrigger(
                        id: "shows-distance",
                        selected: model.distance,
                        triggerLabel: { "Distance \($0.title)" },
                        openDropdownID: $openDropdownID
                    )
                }

                PillDropdownTrigger(
                    id: "shows-sort",
                    selected: model.sort,
                    triggerLabel: { "Sort \($0.title)" },
                    openDropdownID: $openDropdownID
                )

                if model.allowsLocationFiltering {
                    PillSheetTrigger(
                        title: zipChipTitle,
                        systemImage: zipChipSystemImage,
                        isActive: model.activeNearbyPreference != nil,
                        accessibilityLabel: "Edit ZIP",
                        accessibilityHint: zipChipAccessibilityHint
                    ) {
                        isZipEditorPresented = true
                    }
                }

                if activeFilterCount > 0 {
                    Button {
                        isFilterEditorPresented = true
                    } label: {
                        LaughTrackBrowseChip(filterCountTitle, tone: .accent)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Filter results")
                } else {
                    Button("Filters", action: { isFilterEditorPresented = true })
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                        .buttonStyle(.plain)
                        .accessibilityLabel("Filter results")
                }
            } dateScope: {
                PillSheetTrigger(
                    title: model.dateRange.pillLabel(),
                    systemImage: "calendar",
                    isActive: model.dateRange.isActive
                ) {
                    isDateEditorPresented = true
                }
            }

            if model.allowsLocationFiltering, let nearbyStatusMessage = model.nearbyStatusMessage {
                InlineStatusMessage(message: nearbyStatusMessage)
            }

        }
    }

    private var zipChipTitle: String {
        if let activeNearbyPreference = model.activeNearbyPreference {
            return "Location \(activeNearbyPreference.zipCode)"
        }

        let draft = model.zipCodeDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        return draft.isEmpty ? "Location" : "Location \(draft)"
    }

    private var zipChipSystemImage: String {
        guard let source = model.activeNearbyPreference?.source else {
            return "mappin.and.ellipse"
        }
        return source == .geolocated ? "location.fill" : "mappin.and.ellipse"
    }

    private var zipChipAccessibilityHint: String {
        guard let source = model.activeNearbyPreference?.source else {
            return "No location set."
        }
        return source == .geolocated ? "Detected from device location." : "Saved manually."
    }

    private var activeFilterCount: Int {
        model.selectedFilterSlugs.count
    }

    private var filterCountTitle: String {
        "\(activeFilterCount) filter\(activeFilterCount == 1 ? "" : "s")"
    }

}

private struct ShowsDateRangeSheet: View {
    @ObservedObject var model: ShowsListModel
    let apiClient: Client
    @Binding var isPresented: Bool

    @State private var showsByDate: [Date: Int] = [:]

    var body: some View {
        DateRangeFilterSheet(
            filter: $model.dateRange,
            isPresented: $isPresented,
            title: "Date range",
            subtitle: "Choose the show dates to include.",
            showsByDate: showsByDate,
            minimumDate: Calendar.current.startOfDay(for: Date())
        )
        .task(id: DateRangeDensityKey(
            zip: model.activeNearbyPreference?.zipCode,
            distance: model.activeNearbyPreference?.distanceMiles,
            anchorDay: Calendar.current.startOfDay(for: max(model.dateRange.from, Date()))
        )) {
            await loadDensity()
        }
    }

    private func loadDensity() async {
        if let next = await DateRangeDensity.compute(
            preference: model.activeNearbyPreference,
            fromDate: model.dateRange.from,
            now: Date(),
            apiClient: apiClient
        ) {
            showsByDate = next
        }
    }
}

enum DateRangeDensity {
    /// Returns the density map to assign onto `showsByDate`, or `nil` when the
    /// caller should leave its existing state alone. An empty dictionary is
    /// the explicit "clear" signal — the early-return path when there is no
    /// active nearby preference.
    static func compute(
        preference: NearbyPreference?,
        fromDate: Date,
        now: Date,
        apiClient: Client,
        calendar: Calendar = .current
    ) async -> [Date: Int]? {
        guard let preference else { return [:] }

        let today = calendar.startOfDay(for: now)
        let anchor = max(calendar.startOfDay(for: fromDate), today)
        guard let to = calendar.date(byAdding: .day, value: 89, to: anchor) else {
            return nil
        }

        let fromString = isoDateFormatter.string(from: anchor)
        let toString = isoDateFormatter.string(from: to)

        do {
            let output = try await apiClient.getShowsDensity(
                .init(
                    query: .init(
                        zip: preference.zipCode,
                        from: fromString,
                        to: toString,
                        distance: preference.distanceMiles
                    ),
                    headers: .init(xTimezone: TimeZone.autoupdatingCurrent.identifier)
                )
            )
            guard case .ok(let ok) = output, let json = try? ok.body.json else {
                return nil
            }
            return densityMap(from: json.additionalProperties, calendar: calendar)
        } catch {
            // Density dots are best-effort decoration; silently drop on failure.
            return nil
        }
    }

    // Invariant: `calendar.timeZone` must match `isoDateFormatter.timeZone`
    // (currently `TimeZone.autoupdatingCurrent`). The formatter parses midnight
    // in its own timezone, and `startOfDay` re-rounds in the calendar's — a
    // mismatch would bucket some entries onto a neighbouring day.
    static func densityMap(
        from raw: [String: Int],
        calendar: Calendar = .current
    ) -> [Date: Int] {
        var result: [Date: Int] = [:]
        for (key, count) in raw where count > 0 {
            guard let date = isoDateFormatter.date(from: key) else { continue }
            result[calendar.startOfDay(for: date)] = count
        }
        return result
    }

    static let isoDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone.autoupdatingCurrent
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
}

private struct DateRangeDensityKey: Hashable {
    let zip: String?
    let distance: Int?
    let anchorDay: Date
}

