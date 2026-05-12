import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore
#if canImport(UIKit)
import UIKit
#endif

struct ShowsDiscoveryView: View {
    let apiClient: Client
    @ObservedObject var model: ShowsDiscoveryModel
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
                    SearchField(
                        title: "Comedian",
                        prompt: "Mark Normand, Atsuko Okatsuka…",
                        text: $model.comedianSearchText
                    )

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
        #if os(iOS)
        .fadeFullScreenCover(isPresented: $isZipEditorPresented) {
            ZipFilterModal(model: model, isPresented: $isZipEditorPresented)
        }
        .fadeFullScreenCover(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: currentFilters,
                total: currentTotal,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented
            )
        }
        .fadeFullScreenCover(isPresented: $isDateEditorPresented) {
            DateRangeFilterModal(model: model, apiClient: apiClient, isPresented: $isDateEditorPresented)
        }
        #else
        .sheet(isPresented: $isZipEditorPresented) {
            ZipFilterModal(model: model, isPresented: $isZipEditorPresented)
        }
        .sheet(isPresented: $isFilterEditorPresented) {
            SearchFilterModal(
                filters: currentFilters,
                total: currentTotal,
                selectedSlugs: $model.selectedFilterSlugs,
                isPresented: $isFilterEditorPresented
            )
        }
        .sheet(isPresented: $isDateEditorPresented) {
            DateRangeFilterModal(model: model, apiClient: apiClient, isPresented: $isDateEditorPresented)
        }
        #endif
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

    @ObservedObject var model: ShowsDiscoveryModel
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
                    Button {
                        isZipEditorPresented = true
                    } label: {
                        LaughTrackBrowseChip(
                            zipChipTitle,
                            systemImage: zipChipSystemImage,
                            tone: model.activeNearbyPreference == nil ? .neutral : .selected
                        )
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Edit ZIP")
                    .accessibilityHint(zipChipAccessibilityHint)
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
                Button {
                    isDateEditorPresented = true
                } label: {
                    LaughTrackBrowseChip(
                        model.dateRangeChipTitle,
                        systemImage: "calendar",
                        tone: model.useDateRange ? .selected : .neutral
                    )
                }
                .buttonStyle(.plain)
                .accessibilityLabel(model.dateRangeChipTitle)
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

private struct DateRangeFilterModal: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel
    let apiClient: Client
    @Binding var isPresented: Bool

    @State private var showsByDate: [Date: Int] = [:]

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            Color.black.opacity(0.28)
                .ignoresSafeArea()
                .onTapGesture {
                    isPresented = false
                }

            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                HStack(alignment: .top, spacing: theme.spacing.md) {
                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text("Date range")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text("Choose the show dates to include.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    Button {
                        isPresented = false
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: theme.iconSizes.sm, weight: .bold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .frame(width: 36, height: 36)
                            .background(laughTrack.colors.surfaceElevated)
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close")
                }

                ScrollView {
                    MonthCalendarView(
                        selection: .range(
                            start: $model.fromDate,
                            end: Binding(
                                get: { max(model.toDate, model.fromDate) },
                                set: { model.toDate = max($0, model.fromDate) }
                            )
                        ),
                        showsByDate: showsByDate,
                        minimumDate: Calendar.current.startOfDay(for: Date())
                    )
                    .padding(.horizontal, theme.spacing.xs)
                }
                .font(laughTrack.typography.body)
                .frame(maxHeight: 430)

                VStack(spacing: theme.spacing.sm) {
                    LaughTrackButton("Apply", systemImage: "checkmark", density: .compact) {
                        model.useDateRange = true
                        isPresented = false
                    }

                    LaughTrackButton("Today", systemImage: "calendar", tone: .secondary, density: .compact) {
                        let today = Calendar.current.startOfDay(for: Date())
                        model.fromDate = today
                        model.toDate = today
                        model.useDateRange = true
                        isPresented = false
                    }

                    LaughTrackButton("Any date", systemImage: "calendar.badge.minus", tone: .tertiary, density: .compact) {
                        model.useDateRange = false
                        isPresented = false
                    }
                }
            }
            .padding(theme.spacing.xl)
            .background(laughTrack.colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
            .shadowStyle(laughTrack.shadows.floating)
            .padding(.horizontal, theme.spacing.xl)
        }
        .background(.clear)
        .task(id: DateRangeDensityKey(
            zip: model.activeNearbyPreference?.zipCode,
            distance: model.activeNearbyPreference?.distanceMiles
        )) {
            await loadDensity()
        }
    }

    private func loadDensity() async {
        guard let preference = model.activeNearbyPreference else {
            showsByDate = [:]
            return
        }

        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        guard let to = calendar.date(byAdding: .day, value: 89, to: today) else { return }

        let fromString = Self.isoDateFormatter.string(from: today)
        let toString = Self.isoDateFormatter.string(from: to)

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
            guard case .ok(let ok) = output, let json = try? ok.body.json else { return }
            showsByDate = Self.densityMap(from: json.additionalProperties)
        } catch {
            // Density dots are best-effort decoration; silently drop on failure.
        }
    }

    private static func densityMap(from raw: [String: Int]) -> [Date: Int] {
        let calendar = Calendar.current
        var result: [Date: Int] = [:]
        for (key, count) in raw where count > 0 {
            guard let date = isoDateFormatter.date(from: key) else { continue }
            result[calendar.startOfDay(for: date)] = count
        }
        return result
    }

    private static let isoDateFormatter: DateFormatter = {
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
}

private struct ZipFilterModal: View {
    @Environment(\.appTheme) private var theme

    @ObservedObject var model: ShowsDiscoveryModel
    @Binding var isPresented: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            Color.black.opacity(0.28)
                .ignoresSafeArea()
                .onTapGesture {
                    isPresented = false
                }

            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                HStack(alignment: .top, spacing: theme.spacing.md) {
                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text("Location")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text("Set the location used for nearby shows.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    Button {
                        isPresented = false
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: theme.iconSizes.sm, weight: .bold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .frame(width: 36, height: 36)
                            .background(laughTrack.colors.surfaceElevated)
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close")
                }

                LaughTrackSearchField(placeholder: "10012", text: $model.zipCodeDraft) {
                    Button {
                        applyZip()
                    } label: {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: theme.iconSizes.md, weight: .semibold))
                            .foregroundStyle(laughTrack.colors.accent)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Apply ZIP")
                }
                .modifier(SearchFieldInputBehavior())
                #if os(iOS)
                .keyboardType(UIKeyboardType.numberPad)
                #endif
                .onSubmit(applyZip)

                VStack(spacing: theme.spacing.sm) {
                    LaughTrackButton("Apply", systemImage: "checkmark", density: .compact) {
                        applyZip()
                    }

                    LaughTrackButton(
                        model.isResolvingCurrentLocation ? "Finding ZIP..." : "Use my location",
                        systemImage: "location.fill",
                        tone: .secondary,
                        density: .compact
                    ) {
                        Task {
                            let didResolve = await model.useCurrentLocation()
                            if didResolve {
                                isPresented = false
                            }
                        }
                    }
                    .disabled(model.isResolvingCurrentLocation)

                    if model.activeNearbyPreference != nil {
                        LaughTrackButton("Clear", systemImage: "location.slash", tone: .tertiary, density: .compact) {
                            model.clearLocation()
                            isPresented = false
                        }
                    }
                }

                if let nearbyStatusMessage = model.nearbyStatusMessage {
                    InlineStatusMessage(message: nearbyStatusMessage)

                    if nearbyStatusMessage == NearbyLocationError.denied.recoveryMessage {
                        LaughTrackButton("Open Settings", systemImage: "gearshape", tone: .secondary, density: .compact, fullWidth: false) {
                            openAppSettings()
                        }
                    }
                }
            }
            .padding(theme.spacing.xl)
            .background(laughTrack.colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: laughTrack.radius.card, style: .continuous)
                    .stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
            )
            .shadowStyle(laughTrack.shadows.floating)
            .padding(.horizontal, theme.spacing.xl)
        }
        .background(.clear)
    }

    private func applyZip() {
        if model.applyManualZip() {
            isPresented = false
        }
    }

    private func openAppSettings() {
        #if canImport(UIKit)
        guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
        UIApplication.shared.open(url)
        #endif
    }
}
