import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

/// Pure description of which Shows-list chrome is visible for a given mode.
/// Compact mode (used by pinned rails such as club / comedian detail) hides
/// the full comedian/club search fields and the sort + filter pills, keeping
/// only the location and date affordances. Extracted so the behaviour can be
/// verified without hosting the view — HostedView's accessibility-tree wiring
/// is broken on iOS 26.x / 18.6 simulators, so a dump-based assertion is
/// unreliable (TASK-2535).
struct ShowsListChromeVisibility: Equatable {
    let compactMode: Bool
    var displaysSearchFields = true
    var showsSearchFields: Bool { !compactMode && displaysSearchFields }
    var showsSortControl: Bool { !compactMode }
    var showsFilterControl: Bool { !compactMode }
    var showsDateControl: Bool { true }
}

enum ShowsListStandout {
    static func resolveID(in shows: [Components.Schemas.Show]) -> Int? {
        let scored = shows.compactMap { show -> (id: Int, score: Double)? in
            guard let score = show.popularityScore, score > 0 else { return nil }
            return (show.id, score)
        }
        guard let best = scored.max(by: { $0.score < $1.score }) else { return nil }
        let topCount = scored.filter { $0.score == best.score }.count
        return topCount == 1 ? best.id : nil
    }
}

struct ShowAgendaSection: Identifiable, Equatable {
    let day: Date
    let shows: [Components.Schemas.Show]

    var id: Date { day }
}

enum ShowAgenda {
    static func sections(
        from shows: [Components.Schemas.Show],
        calendar: Calendar = .current
    ) -> [ShowAgendaSection] {
        Dictionary(grouping: shows) { calendar.startOfDay(for: $0.date) }
            .map { ShowAgendaSection(day: $0.key, shows: $0.value.sorted { $0.date < $1.date }) }
            .sorted { $0.day < $1.day }
    }
}

enum ShowCalendarDateSync {
    static func selectedDate(
        for dateRange: DateRangeFilter,
        now: Date = Date(),
        calendar: Calendar = .current
    ) -> Date {
        calendar.startOfDay(for: dateRange.isActive ? dateRange.from : now)
    }

    static func exactDateRange(
        for selectedDate: Date,
        calendar: Calendar = .current
    ) -> DateRangeFilter {
        let day = calendar.startOfDay(for: selectedDate)
        return DateRangeFilter(from: day, to: day, isActive: true)
    }
}

struct ShowsListView: View {
    let apiClient: Client
    @ObservedObject var model: ShowsListModel
    var displaysSearchFields = true
    var compactMode = false
    var isActive = true

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var isZipEditorPresented = false
    @State private var isFilterEditorPresented = false
    @State private var isDateEditorPresented = false
    @State private var isOptionalSearchExpanded = false
    @State private var openDropdownID: String?

    private var pageCache: DataCache<LaughTrackCacheKey> {
        serviceContainer.resolve(DataCache<LaughTrackCacheKey>.self)
    }

    private var chrome: ShowsListChromeVisibility {
        ShowsListChromeVisibility(
            compactMode: compactMode,
            displaysSearchFields: displaysSearchFields
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.laughTrackTokens.browseDensity.shelfGap) {
                ShowFiltersPanel(
                    model: model,
                    filters: currentFilters,
                    total: currentTotal,
                    isZipEditorPresented: $isZipEditorPresented,
                    isFilterEditorPresented: $isFilterEditorPresented,
                    isDateEditorPresented: $isDateEditorPresented,
                    openDropdownID: $openDropdownID,
                    compactMode: compactMode
                )

                if chrome.showsSearchFields {
                    DisclosureGroup(isExpanded: $isOptionalSearchExpanded) {
                        VStack(alignment: .leading, spacing: theme.spacing.sm) {
                            if !model.isComedianPinned {
                                SearchField(
                                    title: "Comedian (optional)",
                                    prompt: "Mark Normand, Atsuko Okatsuka…",
                                    text: $model.comedianSearchText
                                )
                            }

                            if !model.isClubPinned {
                                SearchField(
                                    title: "Club (optional)",
                                    prompt: "Comedy Cellar, The Stand…",
                                    text: $model.clubSearchText
                                )
                            }
                        }
                        .padding(.top, theme.spacing.sm)
                    } label: {
                        Label("Add comedian or club", systemImage: "magnifyingglass")
                            .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
                            .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                    }
                }

                if !activeConstraints.isEmpty {
                    ShowActiveConstraintsView(
                        constraints: activeConstraints,
                        remove: model.removeConstraint,
                        clearAll: model.clearAllFilters
                    )
                }

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
                        EmptyCard(
                            title: emptyState.title,
                            message: emptyState.message,
                            actionTitle: emptyState.actionTitle,
                            action: emptyState.actionTitle.map { _ in
                                { model.clearAllFilters() }
                            }
                        )
                    } else {
                        VStack(alignment: .leading, spacing: theme.spacing.md) {
                            if !compactMode {
                                SearchResultsSummary(count: result.items.count, total: result.total)
                            }

                            let pageCount = model.pageCount(for: result.total)
                            if compactMode, pageCount > 1 {
                                LaughTrackPagedControls(
                                    currentPage: result.page,
                                    pageCount: pageCount,
                                    onPrevious: {
                                        Task {
                                            await model.loadPage(
                                                result.page - 1,
                                                apiClient: apiClient,
                                                cache: pageCache
                                            )
                                        }
                                    },
                                    onNext: {
                                        Task {
                                            await model.loadPage(
                                                result.page + 1,
                                                apiClient: apiClient,
                                                cache: pageCache
                                            )
                                        }
                                    }
                                )
                                .disabled(model.isLoadingMore)
                            }

                            if compactMode {
                                showRows(result.items, standoutShowID: ShowsListStandout.resolveID(in: result.items))
                            } else {
                                Picker("Results view", selection: $model.resultsPresentation) {
                                    ForEach(ShowResultsPresentation.allCases) { presentation in
                                        Text(presentation.title).tag(presentation)
                                    }
                                }
                                .pickerStyle(.segmented)
                                .accessibilityLabel("Show results presentation")

                                if model.resultsPresentation == .calendar {
                                    ShowResultsCalendarView(model: model, apiClient: apiClient)
                                }

                                agendaRows(result.items)
                            }

                            if let paginationFailure = model.paginationFailure {
                                InlineStatusMessage(message: paginationFailure.message)
                            }

                            if !compactMode, result.canLoadMore {
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
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .sheet(isPresented: $isZipEditorPresented) {
            LocationFilterSheet(model: model, isPresented: $isZipEditorPresented)
        }
        .sheet(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: secondaryFilters,
                total: currentTotal,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented
            )
            .presentationDetents([.medium, .large])
        }
        .sheet(isPresented: $isDateEditorPresented) {
            ShowsDateRangeSheet(model: model, apiClient: apiClient, isPresented: $isDateEditorPresented)
        }
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

                PillDropdownOverlay(
                    id: "shows-max-price",
                    options: ShowMaximumPriceOption.allCases,
                    selected: $model.maximumPrice,
                    triggerLabel: { $0 == .any ? "Max price" : $0.title },
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

    @ViewBuilder
    private func agendaRows(_ shows: [Components.Schemas.Show]) -> some View {
        let standoutShowID = ShowsListStandout.resolveID(in: shows)
        ForEach(ShowAgenda.sections(from: shows)) { section in
            VStack(alignment: .leading, spacing: theme.spacing.sm) {
                Text(Self.agendaDateFormatter.string(from: section.day))
                    .font(theme.laughTrackTokens.typography.sectionTitle)
                    .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                    .accessibilityAddTraits(.isHeader)
                showRows(section.shows, standoutShowID: standoutShowID)
            }
        }
    }

    @ViewBuilder
    private func showRows(_ shows: [Components.Schemas.Show], standoutShowID: Int?) -> some View {
        AdaptiveSearchResults(spacing: theme.spacing.md) {
            ForEach(shows, id: \.id) { show in
                Button {
                    coordinator.open(.show(show.id))
                } label: {
                    ShowRow(
                        show: show,
                        presentation: show.id == standoutShowID ? .compactTicketProminent : .compactTicket
                    )
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier(LaughTrackViewTestID.showsSearchResultButton(show.id))
            }
        }
    }

    private static let agendaDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.setLocalizedDateFormatFromTemplate("EEEE, MMMM d")
        return formatter
    }()

    private var currentTotal: Int {
        guard case .success(let result) = model.phase else { return 0 }
        return result.total
    }

    private var secondaryFilters: [Components.Schemas.Filter] {
        let primarySlugs = Set(ShowFormatOption.allCases.map(\.rawValue)).union(["free"])
        return currentFilters.filter { !primarySlugs.contains($0.slug) }
    }

    private var activeConstraints: [ShowActiveConstraint] {
        model.activeConstraints(availableFilters: currentFilters)
    }

    private var nationwideComedianSearchMessage: String? {
        guard model.isShowingNationwideComedianSearch else { return nil }
        let name = model.comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines)
        return "Showing nationwide results for \(name). Clear search to use your nearby radius."
    }

    private var emptyState: ShowsListEmptyMessage.Resolution {
        ShowsListEmptyMessage.resolve(
            comedianSearchText: model.comedianSearchText,
            clubSearchText: model.clubSearchText,
            hasActiveNearbyPreference: model.activeNearbyPreference != nil,
            pinnedComedianName: model.pinnedComedianName,
            pinnedClubName: model.pinnedClubName
        )
    }
}

/// Pure resolver for the `ShowsListView` empty-state copy. Extracted so the
/// branching (search-filter → ZIP-filter → pinned-entity → generic) can be
/// covered without hosting the view — HostedView's accessibility-tree wiring
/// is broken on iOS 26.x simulators (see `ios/CLAUDE.md`).
enum ShowsListEmptyMessage {
    struct Resolution: Equatable {
        let title: String
        let message: String
        let actionTitle: String?

        init(title: String, message: String, actionTitle: String? = nil) {
            self.title = title
            self.message = message
            self.actionTitle = actionTitle
        }
    }

    static func resolve(
        comedianSearchText: String,
        clubSearchText: String,
        hasActiveNearbyPreference: Bool,
        pinnedComedianName: String?,
        pinnedClubName: String?
    ) -> Resolution {
        if !comedianSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
            !clubSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return Resolution(
                title: "No shows yet",
                message: "No shows matched this search. Try another comedian, club, or a broader date range."
            )
        }

        if hasActiveNearbyPreference {
            return Resolution(
                title: "No shows yet",
                message: "No shows matched this ZIP code yet. Broaden the radius or clear location filters."
            )
        }

        if let pinnedName = (pinnedComedianName ?? pinnedClubName)?
            .trimmingCharacters(in: .whitespacesAndNewlines), !pinnedName.isEmpty {
            // The pinned-entity branch used to assert the comedian/club had no
            // upcoming shows at all, but the underlying query is filtered by
            // distance + date — a fact users see one row above. The softer
            // copy stays honest about what we actually know.
            return Resolution(
                title: "No matching shows",
                message: "Try broadening your location or date range to see more shows from \(pinnedName).",
                actionTitle: "Clear filters"
            )
        }

        return Resolution(
            title: "No shows yet",
            message: "No shows are available right now."
        )
    }
}

private struct ShowActiveConstraintsView: View {
    @Environment(\.appTheme) private var theme

    let constraints: [ShowActiveConstraint]
    let remove: (ShowActiveConstraintKind) -> Void
    let clearAll: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            HStack {
                Text("Filtered by")
                    .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                Spacer(minLength: 0)
                Button("Clear all", action: clearAll)
                    .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
                    .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
            }

            ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                ForEach(constraints) { constraint in
                    Button {
                        remove(constraint.kind)
                    } label: {
                        LaughTrackBrowseChip(
                            constraint.label,
                            systemImage: "xmark",
                            tone: .accent
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Remove \(constraint.label) filter")
                }
            }
        }
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
    let compactMode: Bool

    private var chrome: ShowsListChromeVisibility {
        ShowsListChromeVisibility(compactMode: compactMode)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            if compactMode {
                LaughTrackSectionHeader(title: "Search dates")
            } else {
                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text("EXPLORE SHOWS")
                        .font(theme.laughTrackTokens.typography.eyebrow)
                        .tracking(1.8)
                        .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
                        .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
                    Text("Start with what matters")
                        .font(theme.laughTrackTokens.typography.sectionTitle)
                        .foregroundStyle(theme.laughTrackTokens.colors.textPrimary)
                    Text("Choose a date, place, price, or kind of comedy. Add a comedian or club only when you want one.")
                        .font(theme.laughTrackTokens.typography.metadata)
                        .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
                }
            }

            ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                if !compactMode {
                    facetButton(
                        title: "Tonight",
                        systemImage: "moon.stars",
                        isSelected: isTonightSelected
                    ) {
                        model.applyDateShortcut("Tonight")
                    }

                    facetButton(
                        title: "This Weekend",
                        systemImage: "sparkles",
                        isSelected: isWeekendSelected
                    ) {
                        model.applyDateShortcut("This Weekend")
                    }

                    facetButton(
                        title: "Free",
                        systemImage: "ticket",
                        isSelected: model.selectedFilterSlugs.contains("free")
                    ) {
                        toggleFilter("free")
                    }

                    facetButton(
                        title: ShowFormatOption.openMic.title,
                        systemImage: "mic",
                        isSelected: model.selectedFilterSlugs.contains(ShowFormatOption.openMic.rawValue)
                    ) {
                        toggleFilter(ShowFormatOption.openMic.rawValue)
                    }
                }

                if model.allowsLocationFiltering {
                    PillSheetTrigger(
                        title: zipChipTitle,
                        systemImage: zipChipSystemImage,
                        isActive: model.activeNearbyPreference != nil,
                        accessibilityLabel: "Edit location",
                        accessibilityHint: zipChipAccessibilityHint
                    ) {
                        isZipEditorPresented = true
                    }
                }

                if model.allowsLocationFiltering {
                    PillDropdownTrigger(
                        id: "shows-distance",
                        selected: model.distance,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Distance \($0.title)" },
                        openDropdownID: $openDropdownID
                    )
                }

                PillSheetTrigger(
                    title: model.dateRange.pillLabel(),
                    systemImage: "calendar",
                    isActive: model.dateRange.isActive
                ) {
                    isDateEditorPresented = true
                }

                if chrome.showsFilterControl {
                    PillDropdownTrigger(
                        id: "shows-max-price",
                        selected: model.maximumPrice,
                        triggerLabel: { $0 == .any ? "Max price" : $0.title },
                        accessibilityLabel: { $0 == .any ? "Maximum price" : $0.title },
                        openDropdownID: $openDropdownID
                    )

                    ForEach(ShowFormatOption.allCases.filter { $0 != .openMic }) { format in
                        facetButton(
                            title: format.title,
                            systemImage: formatSystemImage(format),
                            isSelected: model.selectedFilterSlugs.contains(format.rawValue)
                        ) {
                            toggleFilter(format.rawValue)
                        }
                    }

                    if !secondaryFilters.isEmpty {
                        PillSheetTrigger(
                            title: secondaryFilterCount > 0 ? secondaryFilterCountTitle : "More filters",
                            systemImage: "line.3.horizontal.decrease",
                            isActive: secondaryFilterCount > 0,
                            accessibilityLabel: "More show filters"
                        ) {
                            isFilterEditorPresented = true
                        }
                    }

                    PillDropdownTrigger(
                        id: "shows-sort",
                        selected: model.sort,
                        triggerLabel: { $0.title },
                        accessibilityLabel: { "Sort \($0.title)" },
                        openDropdownID: $openDropdownID
                    )
                }
            }

            if model.allowsLocationFiltering, let nearbyStatusMessage = model.nearbyStatusMessage {
                InlineStatusMessage(message: nearbyStatusMessage)
            }
        }
    }

    private var zipChipTitle: String {
        if let activeLocationLabel = model.activeLocationLabel {
            return "Location \(activeLocationLabel)"
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

    private var secondaryFilters: [Components.Schemas.Filter] {
        let primarySlugs = Set(ShowFormatOption.allCases.map(\.rawValue)).union(["free"])
        return filters.filter { !primarySlugs.contains($0.slug) }
    }

    private var secondaryFilterCount: Int {
        Set(secondaryFilters.map(\.slug)).intersection(model.selectedFilterSlugs).count
    }

    private var secondaryFilterCountTitle: String {
        "\(secondaryFilterCount) more"
    }

    private var isTonightSelected: Bool {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        return model.dateRange.isActive &&
            calendar.isDate(model.dateRange.from, inSameDayAs: today) &&
            calendar.isDate(model.dateRange.to, inSameDayAs: today)
    }

    private var isWeekendSelected: Bool {
        guard model.dateRange.isActive else { return false }
        let calendar = Calendar.current
        return calendar.component(.weekday, from: model.dateRange.to) == 1 &&
            calendar.dateComponents([.day], from: model.dateRange.from, to: model.dateRange.to).day.map { (0...2).contains($0) } == true
    }

    private func toggleFilter(_ slug: String) {
        if model.selectedFilterSlugs.contains(slug) {
            model.selectedFilterSlugs.remove(slug)
        } else {
            model.selectedFilterSlugs.insert(slug)
        }
    }

    private func formatSystemImage(_ format: ShowFormatOption) -> String {
        switch format {
        case .standUp:
            return "microphone"
        case .improv:
            return "theatermasks"
        case .openMic:
            return "person.wave.2"
        }
    }

    private func facetButton(
        title: String,
        systemImage: String,
        isSelected: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            LaughTrackBrowseChip(
                title,
                systemImage: systemImage,
                tone: isSelected ? .accent : .neutral
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

}

private struct ShowResultsCalendarView: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsListModel
    let apiClient: Client

    @State private var selectedDate: Date
    @State private var cacheState = DateRangeDensityCacheState()

    init(model: ShowsListModel, apiClient: Client) {
        self.model = model
        self.apiClient = apiClient
        _selectedDate = State(initialValue: ShowCalendarDateSync.selectedDate(for: model.dateRange))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            Text("Dots show dates with events for the selected location, comedian, or club.")
                .font(theme.laughTrackTokens.typography.metadata)
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)

            MonthCalendarView(
                selection: .single(calendarSelection),
                showsByDate: mergedShowsByDate,
                minimumDate: Calendar.current.startOfDay(for: Date()),
                onDisplayedMonthChange: { monthStart in
                    Task { await loadDensity(for: monthStart) }
                }
            )
            .id(MonthCalendarView.monthStart(for: selectedDate))
        }
        .padding(theme.spacing.md)
        .background(theme.laughTrackTokens.colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .onChange(of: model.dateRange) { newDateRange in
            let synchronizedDate = ShowCalendarDateSync.selectedDate(for: newDateRange)
            guard !Calendar.current.isDate(selectedDate, inSameDayAs: synchronizedDate) else { return }
            selectedDate = synchronizedDate
        }
    }

    private var calendarSelection: Binding<Date> {
        Binding(
            get: { selectedDate },
            set: { newDate in
                selectedDate = Calendar.current.startOfDay(for: newDate)
                model.dateRange = ShowCalendarDateSync.exactDateRange(for: newDate)
                model.sort = .earliest
            }
        )
    }

    private var mergedShowsByDate: [Date: Int] {
        cacheState.entries.values.reduce(into: [:]) { result, entry in
            result.merge(entry) { _, new in new }
        }
    }

    private func loadDensity(for monthStart: Date) async {
        let query = model.requestKey
        let signature = densitySignature(query)
        guard cacheState.needsFetch(monthStart: monthStart, signature: signature) else { return }

        let calendar = Calendar.current
        guard let nextMonth = calendar.date(byAdding: .month, value: 1, to: monthStart),
              let monthEnd = calendar.date(byAdding: .day, value: -1, to: nextMonth)
        else { return }

        guard let entry = await DateRangeDensity.compute(
            preference: effectiveNearbyPreference,
            comedian: query.comedian.nonEmpty,
            clubId: query.clubId,
            club: query.club.nonEmpty,
            fromDate: monthStart,
            toDate: monthEnd,
            now: Date(),
            apiClient: apiClient
        ) else { return }

        cacheState.storeIfSignatureMatches(entry, forMonthStart: monthStart, signature: signature)
    }

    private var effectiveNearbyPreference: NearbyPreference? {
        model.allowsLocationFiltering ? model.activeNearbyPreference : nil
    }

    private func densitySignature(_ query: ShowsListQuery) -> String {
        "z:\(query.sanitizedZip ?? "")|d:\(query.distance.rawValue)|c:\(query.comedian)|vi:\(query.clubId.map(String.init) ?? "")|v:\(query.club)"
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

        let query = model.requestKey
        guard let entry = await DateRangeDensity.compute(
            preference: effectiveNearbyPreference,
            comedian: query.comedian.nonEmpty,
            clubId: query.clubId,
            club: query.club.nonEmpty,
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
        let query = model.requestKey
        let pref = effectiveNearbyPreference
        let comedian = query.comedian
        let clubId = query.clubId.map(String.init) ?? ""
        let club = query.club
        return "z:\(pref?.zipCode ?? "")|d:\(pref?.distanceMiles ?? 0)|c:\(comedian)|vi:\(clubId)|v:\(club)"
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
        clubId: Int? = nil,
        club: String? = nil,
        fromDate: Date,
        toDate: Date? = nil,
        now: Date,
        apiClient: Client,
        calendar: Calendar = .current
    ) async -> [Date: Int]? {
        let trimmedComedian = comedian?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
        let trimmedClub = clubId == nil
            ? club?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty
            : nil

        guard preference != nil || trimmedComedian != nil || clubId != nil || trimmedClub != nil else {
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
                        club: trimmedClub,
                        clubId: clubId
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
