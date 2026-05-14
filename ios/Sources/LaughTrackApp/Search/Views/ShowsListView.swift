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

                if let message = nationwideComedianSearchMessage {
                    Text(message)
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

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
                    triggerLabel: { $0.title },
                    optionLabel: { $0.title },
                    openDropdownID: $openDropdownID,
                    anchors: anchors,
                    proxy: proxy
                )

                PillDropdownOverlay(
                    id: "shows-sort",
                    options: ShowSortOption.allCases,
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

    private var nationwideComedianSearchMessage: String? {
        guard model.isShowingNationwideComedianSearch else { return nil }
        let name = model.comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines)
        return "Showing nationwide results for \(name). Clear search to use your nearby radius."
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
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            HStack(spacing: theme.spacing.sm) {
                if model.allowsLocationFiltering {
                    PillDropdownTrigger(
                        id: "shows-distance",
                        selected: model.distance,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Distance \($0.title)" },
                        openDropdownID: $openDropdownID
                    )
                }

                PillDropdownTrigger(
                    id: "shows-sort",
                    selected: model.sort,
                    triggerLabel: { $0.title },
                    accessibilityLabel: { "Sort \($0.title)" },
                    openDropdownID: $openDropdownID
                )

                Spacer(minLength: 0)
            }

            HStack(spacing: theme.spacing.sm) {
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

                PillSheetTrigger(
                    title: model.dateRange.pillLabel(),
                    systemImage: "calendar",
                    isActive: model.dateRange.isActive
                ) {
                    isDateEditorPresented = true
                }

                Spacer(minLength: 0)
            }

            HStack(spacing: theme.spacing.sm) {
                PillSheetTrigger(
                    title: activeFilterCount > 0 ? filterCountTitle : "Filters",
                    systemImage: "line.3.horizontal.decrease",
                    isActive: activeFilterCount > 0,
                    accessibilityLabel: "Filter results"
                ) {
                    isFilterEditorPresented = true
                }

                Spacer(minLength: 0)
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

    @State private var cacheState = DateRangeDensityCacheState()

    var body: some View {
        DateRangeFilterSheet(
            filter: $model.dateRange,
            isPresented: $isPresented,
            title: "Date range",
            subtitle: "Choose the show dates to include.",
            showsByDate: mergedShowsByDate,
            minimumDate: Calendar.current.startOfDay(for: Date()),
            onDisplayedMonthChange: { newMonth in
                Task { await loadDensity(for: newMonth) }
            }
        )
    }

    // Merged across every cached month so swiping back to a previously-fetched
    // month paints its dots without re-issuing the request.
    private var mergedShowsByDate: [Date: Int] {
        cacheState.entries.values.reduce(into: [:]) { acc, map in
            for (date, count) in map {
                acc[date] = count
            }
        }
    }

    private func loadDensity(for monthStart: Date) async {
        let signature = currentSignature
        // Synchronous pre-fetch cache check: clears stale entries if the scope
        // changed, then signals miss/hit before any await. Two concurrent
        // loaders cannot end up holding the same empty snapshot because the
        // mutation happens on the live @State, not a copy.
        guard cacheState.needsFetch(monthStart: monthStart, signature: signature) else { return }

        let calendar = Calendar.current
        guard let nextMonthStart = calendar.date(byAdding: .month, value: 1, to: monthStart),
              let lastDayOfMonth = calendar.date(byAdding: .day, value: -1, to: nextMonthStart)
        else { return }

        guard let entry = await DateRangeDensity.compute(
            preference: effectiveNearbyPreference,
            comedian: model.pinnedComedianName,
            club: model.pinnedClubName,
            fromDate: monthStart,
            toDate: lastDayOfMonth,
            now: Date(),
            apiClient: apiClient
        ) else { return }

        // Stale-write guard: the await may have yielded long enough for
        // another loader to invalidate the cache (signature change). Drop the
        // entry on the floor in that case rather than smuggling a stale dot
        // map into the new scope.
        cacheState.storeIfSignatureMatches(entry, forMonthStart: monthStart, signature: signature)
    }

    // Mirrors `ShowsListModel.requestKey`'s zip-handling: on club-pinned views
    // (`allowsLocationFiltering` false) the user's stored nearby preference is
    // intentionally ignored so the density call doesn't smuggle zip/distance
    // into a request that the shows-list itself wouldn't send.
    private var effectiveNearbyPreference: NearbyPreference? {
        model.allowsLocationFiltering ? model.activeNearbyPreference : nil
    }

    private var currentSignature: String {
        let pref = effectiveNearbyPreference
        let comedian = model.pinnedComedianName ?? ""
        let club = model.pinnedClubName ?? ""
        return "z:\(pref?.zipCode ?? "")|d:\(pref?.distanceMiles ?? 0)|c:\(comedian)|v:\(club)"
    }
}

enum DateRangeDensity {
    /// Returns the density map to assign onto `showsByDate`, or `nil` when the
    /// caller should leave its existing state alone. An empty dictionary is
    /// the explicit "clear" signal — the early-return path when nothing
    /// scopes the request: no nearby preference, no pinned comedian, no
    /// pinned club. With an entity pinned the request still goes out even
    /// without a zip, so detail-page calendars can paint dots for the full
    /// entity's calendar regardless of the user's location filter.
    ///
    /// `toDate` defaults to `fromDate + 89 days` to preserve the original
    /// 3-month window for nearby-only callers; per-month callers pass an
    /// explicit end-of-month date so the cache key matches the fetch window.
    static func compute(
        preference: NearbyPreference?,
        comedian: String? = nil,
        club: String? = nil,
        fromDate: Date,
        toDate: Date? = nil,
        now: Date,
        apiClient: Client,
        calendar: Calendar = .current
    ) async -> [Date: Int]? {
        let trimmedComedian = comedian?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        let trimmedClub = club?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty

        guard preference != nil || trimmedComedian != nil || trimmedClub != nil else {
            return [:]
        }

        let today = calendar.startOfDay(for: now)
        let anchor = max(calendar.startOfDay(for: fromDate), today)
        let resolvedTo: Date
        if let toDate {
            resolvedTo = max(calendar.startOfDay(for: toDate), anchor)
        } else {
            guard let computed = calendar.date(byAdding: .day, value: 89, to: anchor) else {
                return nil
            }
            resolvedTo = computed
        }

        let fromString = isoDateFormatter.string(from: anchor)
        let toString = isoDateFormatter.string(from: resolvedTo)

        do {
            let output = try await apiClient.getShowsDensity(
                .init(
                    query: .init(
                        zip: preference?.zipCode,
                        from: fromString,
                        to: toString,
                        distance: preference?.distanceMiles,
                        comedian: trimmedComedian,
                        club: trimmedClub
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

/// Per-month density cache state owned by `ShowsDateRangeSheet`. Held as
/// `@State`; mutations go through the two `mutating` methods below so the
/// pre-fetch check and the post-fetch write are both synchronous, single-step
/// updates to the live store. This is the reentrancy-safe alternative to
/// snapshot-and-overwrite, which loses concurrent writers' entries when two
/// rapid month swipes await fetches simultaneously.
///
/// The `signature` field scopes the cache to a specific (zip, distance,
/// comedian, club) tuple. When the signature changes — typically because the
/// user changed their nearby zip on a comedian detail page where location
/// filtering is enabled — the cache invalidates so stale dots cannot leak
/// into the new scope.
struct DateRangeDensityCacheState: Equatable {
    var entries: [Date: [Date: Int]] = [:]
    var signature: String?

    /// Returns `true` iff the caller should fetch `monthStart` for the given
    /// signature. Side-effect: if the signature has changed since the last
    /// load, the entries map is cleared and the signature recorded. Run
    /// synchronously immediately before awaiting the fetch.
    @discardableResult
    mutating func needsFetch(monthStart: Date, signature: String) -> Bool {
        if self.signature != signature {
            entries = [:]
            self.signature = signature
        }
        return entries[monthStart] == nil
    }

    /// Stores `entry` only when the cache's current signature still matches
    /// the one that was active when the fetch started. A mismatch means a
    /// concurrent loader changed scope while this load was awaiting; the
    /// entry is discarded so it cannot poison the new scope's dot map.
    mutating func storeIfSignatureMatches(
        _ entry: [Date: Int],
        forMonthStart monthStart: Date,
        signature: String
    ) {
        guard self.signature == signature else { return }
        entries[monthStart] = entry
    }
}
