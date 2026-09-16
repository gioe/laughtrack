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

    func showsResultsStatus(for state: SearchResultsState) -> Bool {
        !compactMode || !state.isConfirmed
    }
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
        Dictionary(grouping: shows) {
            ShowFormatting.calendarDay($0.date, timezoneID: $0.timezone, calendar: calendar)
        }
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
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    @State private var isZipEditorPresented = false
    @State private var isFilterEditorPresented = false
    @State private var isDateEditorPresented = false
    @State private var isOptionalSearchExpanded = false

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
        VStack(alignment: .leading, spacing: theme.spacing.md) {
                ShowFiltersPanel(
                    model: model,
                    isZipEditorPresented: $isZipEditorPresented,
                    isFilterEditorPresented: $isFilterEditorPresented,
                    isDateEditorPresented: $isDateEditorPresented,
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
                            .frame(minHeight: 44)
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
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        if !compactMode {
                            resultsToolbar(count: 0, total: 0, state: .confirmed, isLoading: true)
                            if model.resultsPresentation == .calendar {
                                ShowResultsCalendarView(model: model, apiClient: apiClient)
                            }
                        }
                        ShowsListSkeleton(context: compactMode ? .standalone : .agenda, usesAdaptiveLayout: true)
                    }
                case .failure(let failure):
                    FailureCard(
                        failure: failure,
                        retry: { await model.reload(apiClient: apiClient, cache: pageCache) },
                        signIn: { coordinator.push(.profile) }
                    )
                case .success(let result):
                    let state = model.resultsState(for: model.requestKey)
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        if chrome.showsResultsStatus(for: state) {
                            resultsToolbar(count: result.items.count, total: result.total, state: state)
                        }
                        if result.items.isEmpty {
                            EmptyCard(
                                title: state.isConfirmed ? emptyState.title : "No previous results",
                                message: state.isConfirmed ? emptyState.message : "Results for your updated search will appear here.",
                                actionTitle: state.isConfirmed ? emptyState.actionTitle : nil,
                                action: emptyState.actionTitle.map { _ in
                                    { model.clearAllFilters() }
                                }
                            )
                        } else {
                            VStack(alignment: .leading, spacing: theme.spacing.md) {
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
                                    .disabled(model.isLoadingMore || !state.isConfirmed)
                                }

                                if compactMode {
                                    showRows(result.items, standoutShowID: ShowsListStandout.resolveID(in: result.items))
                                } else {
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
                                    .disabled(!state.isConfirmed)
                                }
                            }
                            .modifier(SearchRefreshAppearance(state: state))
                        }
                    }
                }
            }
        .task(id: DiscoveryLoadTaskKey(isActive: isActive, query: model.requestKey)) {
            guard isActive else { return }
            await model.reload(apiClient: apiClient, cache: pageCache)
        }
        .sheet(isPresented: $isZipEditorPresented) {
            LocationFilterSheet(model: model, isPresented: $isZipEditorPresented, distance: $model.distance)
        }
        .sheet(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: secondaryFilters,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented,
                maximumPrice: $model.maximumPrice,
                preview: model.makeFilterPreview(apiClient: apiClient)
            )
            .presentationDetents([.medium, .large])
        }
        .sheet(isPresented: $isDateEditorPresented) {
            ShowsDateRangeSheet(model: model, apiClient: apiClient, isPresented: $isDateEditorPresented)
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
                showRows(section.shows, standoutShowID: standoutShowID, context: .agenda)
            }
        }
    }

    @ViewBuilder
    private func showRows(
        _ shows: [Components.Schemas.Show],
        standoutShowID: Int?,
        context: ShowRowContext = .standalone
    ) -> some View {
        AdaptiveSearchResults(spacing: theme.spacing.md) {
            ForEach(shows, id: \.id) { show in
                Button {
                    coordinator.open(.show(show.id))
                } label: {
                    ShowRow(
                        show: show,
                        presentation: show.id == standoutShowID ? .compactTicketProminent : .compactTicket,
                        context: context
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

    private var secondaryFilters: [Components.Schemas.Filter] {
        currentFilters.filter { ShowFilterFacetTaxonomy.isSecondary(slug: $0.slug) }
    }

    private func resultsToolbar(count: Int, total: Int, state: SearchResultsState, isLoading: Bool = false) -> some View {
        let layout = dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.xs))
            : AnyLayout(HStackLayout(spacing: theme.spacing.sm))
        return layout {
            if isLoading {
                SearchLoadingSummary().detailSkeletonShimmer()
            } else {
                SearchResultsSummary(
                    count: count, total: total, state: state,
                    retry: { await model.reload(apiClient: apiClient, cache: pageCache) },
                    signIn: { coordinator.push(.profile) }
                )
            }
            if !compactMode {
                HStack(spacing: theme.spacing.sm) {
                    Menu {
                        Picker("Sort shows", selection: $model.sort) {
                            ForEach(ShowSortOption.allCases) { option in
                                Text(option.title).tag(option)
                            }
                        }
                    } label: {
                        Label(model.sort.title, systemImage: "arrow.up.arrow.down")
                            .font(theme.laughTrackTokens.typography.metadata)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(minWidth: 44, minHeight: 44)
                            .contentShape(Rectangle())
                    }
                    .accessibilityLabel("Sort shows")
                    .accessibilityValue(model.sort.title)
                    if dynamicTypeSize.isAccessibilitySize { Spacer(minLength: 12) }
                    Menu {
                        Picker("Results view", selection: $model.resultsPresentation) {
                            ForEach(ShowResultsPresentation.allCases) { presentation in
                                Text(presentation.title).tag(presentation)
                            }
                        }
                    } label: {
                        Image(systemName: model.resultsPresentation == .agenda ? "list.bullet" : "calendar")
                            .font(.system(size: 18, weight: .semibold))
                            .frame(width: 44, height: 44)
                            .contentShape(Rectangle())
                    }
                    .accessibilityLabel("Show results presentation")
                    .accessibilityValue(model.resultsPresentation.title)
                }
                .foregroundStyle(theme.laughTrackTokens.colors.textSecondary)
            }
        }
    }

    private var activeConstraints: [ShowActiveConstraint] {
        model.activeConstraints(availableFilters: currentFilters).filter {
            $0.kind != .location && $0.kind != .date
        }
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
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

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
                    .frame(minWidth: 44, minHeight: 44)
            }

            let layout = dynamicTypeSize.isAccessibilitySize
                ? AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.sm))
                : AnyLayout(ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm))
            layout {
                ForEach(constraints) { constraint in
                    Button {
                        remove(constraint.kind)
                    } label: {
                        Label(constraint.label, systemImage: "xmark")
                            .font(theme.laughTrackTokens.typography.metadata)
                            .fixedSize(horizontal: false, vertical: true)
                            .foregroundStyle(theme.laughTrackTokens.colors.accentStrong)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .frame(minHeight: 44)
                            .background(theme.laughTrackTokens.colors.accentMuted.opacity(0.25), in: RoundedRectangle(cornerRadius: 12))
                            .contentShape(Rectangle())
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
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @ObservedObject var model: ShowsListModel
    @Binding var isZipEditorPresented: Bool
    @Binding var isFilterEditorPresented: Bool
    @Binding var isDateEditorPresented: Bool
    let compactMode: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: theme.spacing.sm) {
            if compactMode {
                LaughTrackSectionHeader(title: "Search dates")
            }
            let layout = dynamicTypeSize.isAccessibilitySize
                ? AnyLayout(VStackLayout(alignment: .leading, spacing: theme.spacing.xs))
                : AnyLayout(HStackLayout(spacing: theme.spacing.sm))
            layout {
                if model.allowsLocationFiltering {
                    headerButton(locationTitle, systemImage: "mappin.and.ellipse", active: model.activeNearbyPreference != nil) {
                        isZipEditorPresented = true
                    }
                    .accessibilityLabel("Edit location and radius")
                    .accessibilityValue(locationTitle)
                    .accessibilityIdentifier(LaughTrackViewTestID.showsSearchScreen)
                }
                if !compactMode {
                    if !dynamicTypeSize.isAccessibilitySize { Spacer(minLength: 0) }
                    headerButton(filterCount == 0 ? "Filters" : "Filters (\(filterCount))", systemImage: "line.3.horizontal.decrease", active: filterCount > 0) {
                        isFilterEditorPresented = true
                    }
                    .accessibilityLabel("Show filters")
                }
            }
            if compactMode {
                headerButton(model.dateRange.pillLabel(), systemImage: "calendar", active: model.dateRange.isActive) {
                    isDateEditorPresented = true
                }
            } else {
                layout {
                    ForEach(ShowHeaderDateChoice.allCases) { choice in
                        headerButton(choice.title, active: choice.matches(model.dateRange)) {
                            model.applyDateShortcut(choice.rawValue)
                        }
                        .accessibilityAddTraits(choice.matches(model.dateRange) ? .isSelected : [])
                    }
                    Button {
                        isDateEditorPresented = true
                    } label: {
                        Image(systemName: "calendar")
                            .font(.system(size: 18, weight: .semibold))
                            .frame(width: 44, height: 44)
                            .background(theme.laughTrackTokens.colors.surfaceElevated, in: RoundedRectangle(cornerRadius: 12))
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Choose dates")
                    .accessibilityValue(model.dateRange.pillLabel())
                }
                if model.dateRange.isActive && !ShowHeaderDateChoice.allCases.contains(where: { $0.matches(model.dateRange) }) {
                    headerButton(model.dateRange.pillLabel(), systemImage: "calendar", active: true) {
                        isDateEditorPresented = true
                    }
                }
            }
            if model.allowsLocationFiltering, let message = model.nearbyStatusMessage {
                InlineStatusMessage(message: message)
            }
        }
    }

    private var locationTitle: String {
        if model.isShowingNationwideComedianSearch { return "Nationwide" }
        guard let location = model.activeLocationLabel else { return "Anywhere" }
        return "\(location) · \(model.distance.title)"
    }

    private var filterCount: Int {
        model.selectedFilterSlugs.count + (model.maximumPrice == .any ? 0 : 1)
    }

    private func headerButton(_ title: String, systemImage: String? = nil, active: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 5) {
                if let systemImage { Image(systemName: systemImage) }
                Text(title).fixedSize(horizontal: false, vertical: true)
            }
            .font(theme.laughTrackTokens.typography.metadata.weight(.semibold))
            .foregroundStyle(active ? theme.laughTrackTokens.colors.accentStrong : theme.laughTrackTokens.colors.textPrimary)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .frame(minHeight: 44)
            .background(active ? theme.laughTrackTokens.colors.accentMuted.opacity(0.25) : theme.laughTrackTokens.colors.surfaceElevated, in: RoundedRectangle(cornerRadius: 12))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
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
            Text("Dates and times are local to each venue. Dots mark dates with shows.")
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
            subtitle: "Choose dates at the venue. Show times stay local to each venue.",
            showsByDate: mergedShowsByDate,
            minimumDate: Calendar.current.startOfDay(for: Date()),
            todayTitle: "Tonight",
            quickActions: [
                DateRangeFilterQuickAction(
                    title: "This Weekend",
                    systemImage: "sparkles"
                ) {
                    model.applyDateShortcut("This Weekend")
                },
            ],
            onApply: { _ in
                model.sort = .earliest
            },
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

        let formatter = makeISODateFormatter(calendar: calendar)
        let fromString = formatter.string(from: anchor)
        let toString = formatter.string(from: resolvedTo)

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
                        clubId: clubId,
                        dateBasis: "venue"
                    ),
                    headers: .init(xTimezone: calendar.timeZone.identifier)
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

    // API keys are venue-local civil dates. Decode into the UI calendar without
    // shifting the label through an unrelated timezone.
    static func densityMap(
        from raw: [String: Int],
        calendar: Calendar = .current
    ) -> [Date: Int] {
        var result: [Date: Int] = [:]
        let formatter = makeISODateFormatter(calendar: calendar)
        for (key, count) in raw where count > 0 {
            guard let date = formatter.date(from: key) else { continue }
            result[calendar.startOfDay(for: date)] = count
        }
        return result
    }

    static let isoDateFormatter = makeISODateFormatter(calendar: .current)

    private static func makeISODateFormatter(calendar: Calendar) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }
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
