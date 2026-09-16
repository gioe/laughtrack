import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

/// A presentation owns its choices and preview requests. Dismissal never writes
/// to the live query; only the explicit Apply action publishes the selection.
@MainActor
final class SearchFilterDraft: ObservableObject {
    struct Selection: Hashable {
        var slugs: Set<String>
        var maximumPrice: ShowMaximumPriceOption = .any
    }

    enum Preview: Equatable {
        case updating
        case ready(Int)
        case failed

        var message: String {
            switch self {
            case .updating: "Updating results…"
            case .ready(let count): "\(count.formatted()) \(count == 1 ? "result" : "results")"
            case .failed: "Preview unavailable"
            }
        }
    }

    typealias FetchPreview = @MainActor (Selection) async -> Result<Int, LoadFailure>

    let filters: [Components.Schemas.Filter]
    @Published private(set) var selection: Selection
    @Published private(set) var preview: Preview = .updating
    @Published private(set) var revision = 0
    private let fetchPreview: FetchPreview
    private var isClosed = false

    init(filters: [Components.Schemas.Filter], selection: Selection, preview: @escaping FetchPreview) {
        var seen = Set<String>()
        self.filters = filters.filter { seen.insert($0.slug).inserted }
        self.selection = selection
        self.fetchPreview = preview
    }

    func update(_ selection: Selection) {
        guard !isClosed, self.selection != selection else { return }
        self.selection = selection
        retry()
    }

    func toggle(_ slug: String) {
        var next = selection
        if !next.slugs.insert(slug).inserted { next.slugs.remove(slug) }
        update(next)
    }

    func retry() {
        guard !isClosed else { return }
        preview = .updating
        revision += 1
    }

    func refreshPreview(debounce: Bool = true) async {
        guard !isClosed else { return }
        let requestRevision = revision
        let requestedSelection = selection
        if debounce {
            do { try await Task.sleep(for: .milliseconds(250)) }
            catch { return }
        }
        guard !Task.isCancelled, requestRevision == revision, !isClosed else { return }
        let result = await fetchPreview(requestedSelection)
        // Revision also rejects an old A response after an A → B → A sequence,
        // even if the transport ignores cancellation.
        guard !Task.isCancelled, requestRevision == revision, !isClosed else { return }
        switch result {
        case .success(let count): preview = .ready(count)
        case .failure: preview = .failed
        }
    }

    func apply(_ commit: (Selection) -> Void) {
        guard !isClosed else { return }
        close()
        commit(selection)
    }

    func close() {
        isClosed = true
        revision += 1
    }
}


struct SearchFilterModal: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @StateObject private var draft: SearchFilterDraft
    @Binding var isPresented: Bool
    private let includesPrice: Bool
    private let commit: (SearchFilterDraft.Selection) -> Void

    init(
        filters: [Components.Schemas.Filter],
        selectedSlugs: Binding<Set<String>>,
        isPresented: Binding<Bool>,
        maximumPrice: Binding<ShowMaximumPriceOption>? = nil,
        preview: @escaping SearchFilterDraft.FetchPreview
    ) {
        _draft = StateObject(wrappedValue: SearchFilterDraft(
            filters: filters,
            selection: .init(slugs: selectedSlugs.wrappedValue, maximumPrice: maximumPrice?.wrappedValue ?? .any),
            preview: preview
        ))
        _isPresented = isPresented
        includesPrice = maximumPrice != nil
        commit = { selection in
            selectedSlugs.wrappedValue = selection.slugs
            maximumPrice?.wrappedValue = selection.maximumPrice
        }
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ScrollView {
            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                HStack(alignment: .top, spacing: theme.spacing.md) {
                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text("REFINE SEARCH")
                            .font(.system(size: 11, weight: .heavy, design: .rounded))
                            .tracking(2.2)
                            .foregroundStyle(laughTrack.colors.accentStrong)

                        Text("Filter results")
                            .font(laughTrack.typography.sectionTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text(!includesPrice
                             ? "Preview your choices, then apply them to your search."
                             : "Choose a price limit or kind of comedy.")
                            .font(laughTrack.typography.metadata)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    Spacer(minLength: 0)

                    Button(action: cancel) {
                        Image(systemName: "xmark")
                            .font(.system(size: theme.iconSizes.sm, weight: .bold))
                            .foregroundStyle(laughTrack.colors.textPrimary)
                            .frame(width: 44, height: 44)
                            .background(laughTrack.colors.surfaceElevated)
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Close")
                }

                Group {
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        if includesPrice {
                            Text("Maximum price")
                                .font(laughTrack.typography.metadata.weight(.semibold))
                                .foregroundStyle(laughTrack.colors.textSecondary)
                            Picker("Maximum price", selection: Binding(
                                get: { draft.selection.maximumPrice },
                                set: { draft.update(.init(slugs: draft.selection.slugs, maximumPrice: $0)) }
                            )) {
                                ForEach(ShowMaximumPriceOption.allCases) { option in
                                    Text(option.title).tag(option)
                                }
                            }
                            .pickerStyle(.menu)
                            .tint(laughTrack.colors.accentStrong)
                            .frame(minHeight: 44)
                            .accessibilityIdentifier("search-filter-price")
                            .accessibilityValue(draft.selection.maximumPrice.title)
                        }

                        if draft.filters.isEmpty {
                            if !includesPrice {
                                Text("No filters available for this search.")
                                    .font(laughTrack.typography.metadata)
                                    .foregroundStyle(laughTrack.colors.textSecondary)
                                    .padding(.vertical, theme.spacing.md)
                            }
                        } else {
                            Text("Filter By")
                                .font(laughTrack.typography.metadata.weight(.semibold))
                                .foregroundStyle(laughTrack.colors.textSecondary)

                            if dynamicTypeSize.isAccessibilitySize {
                                VStack(alignment: .leading, spacing: theme.spacing.sm) {
                                    filterChips
                                }
                            } else {
                                ChipFlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                                    filterChips
                                }
                            }
                        }
                    }
                    .padding(.vertical, 2)
                }

                Button {
                    draft.update(.init(slugs: []))
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.system(size: 12, weight: .bold))
                        Text("Reset all filters")
                            .font(laughTrack.typography.metadata.weight(.semibold))
                    }
                    .foregroundStyle(
                        !hasActiveFilters
                            ? laughTrack.colors.textSecondary.opacity(0.45)
                            : laughTrack.colors.textSecondary
                    )
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .frame(minHeight: 44)
                    .overlay(
                        Capsule(style: .continuous)
                            .strokeBorder(
                                (!hasActiveFilters
                                    ? laughTrack.colors.textSecondary.opacity(0.25)
                                    : laughTrack.colors.textSecondary.opacity(0.6)),
                                lineWidth: 1
                            )
                    )
                }
                .buttonStyle(.plain)
                .disabled(!hasActiveFilters)
                .accessibilityLabel("Reset all filters")
                .accessibilityHint(hasActiveFilters
                    ? (!includesPrice ? "Clears the selected filters." : "Clears the selected filters and price limit.")
                    : "No filters are currently applied.")

                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, theme.spacing.xl)
            .padding(.bottom, theme.spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(LaughTrackAtmosphereBackground())
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: theme.spacing.sm) {
                Text(draft.preview.message)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("search-filter-preview")
                if draft.preview == .failed {
                    Button("Retry preview") { draft.retry() }
                        .font(laughTrack.typography.metadata.weight(.semibold))
                        .tint(laughTrack.colors.accentStrong)
                        .frame(minHeight: 44)
                }
                Button {
                    draft.apply(commit)
                    isPresented = false
                } label: {
                    Text("Apply filters")
                        .font(laughTrack.typography.metadata.weight(.bold))
                        .foregroundStyle(Color.white)
                        .padding(.horizontal, theme.spacing.md)
                        .padding(.vertical, theme.spacing.md)
                        .frame(maxWidth: .infinity, minHeight: 48)
                        .background(laughTrack.colors.accentStrong, in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("search-filter-apply")
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.vertical, theme.spacing.md)
            .frame(maxWidth: .infinity)
            .background(laughTrack.colors.surfaceElevated)
        }
        .task(id: draft.revision) { await draft.refreshPreview() }
        .onDisappear { draft.close() }
    }

    private var filterChips: some View {
        ForEach(draft.filters, id: \.slug) { filter in
            FilterMarqueeChip(
                title: filter.name,
                isSelected: draft.selection.slugs.contains(filter.slug)
            ) {
                draft.toggle(filter.slug)
            }
        }
    }

    private var hasActiveFilters: Bool {
        !draft.selection.slugs.isEmpty || draft.selection.maximumPrice != .any
    }

    private func cancel() {
        draft.close()
        isPresented = false
    }
}

/// Marquee-themed filter chip — uppercase rounded heavy text wrapped in the
/// same dashed bulb-ring border + accent glow we use on the primitive filter
/// pills and marquee posters, so selection stands out without a solid fill.
private struct FilterMarqueeChip: View {
    @Environment(\.appTheme) private var theme

    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Button(action: action) {
            Text(title.uppercased())
                .font(laughTrack.typography.metadata.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(isSelected ? laughTrack.colors.accentStrong : laughTrack.colors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .frame(minHeight: 44)
                .background(
                    Capsule(style: .continuous)
                        .fill(isSelected ? laughTrack.colors.accentMuted.opacity(0.18) : Color.clear)
                )
                .overlay(
                    Capsule(style: .continuous)
                        .strokeBorder(
                            isSelected ? laughTrack.colors.accentStrong : laughTrack.colors.accentMuted.opacity(0.7),
                            style: StrokeStyle(
                                lineWidth: isSelected ? 1.8 : 1.4,
                                lineCap: .round,
                                lineJoin: .round,
                                dash: [0.5, 5]
                            )
                        )
                        .shadow(
                            color: laughTrack.colors.accentStrong.opacity(isSelected ? 0.55 : 0.18),
                            radius: isSelected ? 4 : 2
                        )
                )
                .contentShape(Capsule(style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }
}

struct ChipFlowLayout: Layout {
    var spacing: CGFloat
    var rowSpacing: CGFloat

    func sizeThatFits(
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout Void
    ) -> CGSize {
        layout(in: proposal.width, subviews: subviews).size
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout Void
    ) {
        for item in layout(in: bounds.width, subviews: subviews).items {
            subviews[item.index].place(
                at: CGPoint(x: bounds.minX + item.frame.minX, y: bounds.minY + item.frame.minY),
                proposal: ProposedViewSize(item.frame.size)
            )
        }
    }

    private func layout(in maxWidth: CGFloat?, subviews: Subviews) -> (items: [(index: Int, frame: CGRect)], size: CGSize) {
        var items: [(index: Int, frame: CGRect)] = []
        var cursor = CGPoint.zero
        var rowHeight: CGFloat = 0
        var width: CGFloat = 0

        for index in subviews.indices {
            var size = subviews[index].sizeThatFits(.unspecified)
            // Large text or a long location can exceed the whole column.
            // Remeasure within the proposal so a chip cannot widen its parent
            // and push sibling result rows beyond the screen. A zero-width
            // minimum proposal must remain distinct from an unspecified width.
            if let maxWidth, maxWidth.isFinite, size.width > maxWidth {
                size = subviews[index].sizeThatFits(ProposedViewSize(width: max(0, maxWidth), height: nil))
            }
            if cursor.x > 0, let maxWidth, cursor.x + size.width > maxWidth {
                cursor.x = 0
                cursor.y += rowHeight + rowSpacing
                rowHeight = 0
            }

            items.append((index, CGRect(origin: cursor, size: size)))
            cursor.x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            width = max(width, cursor.x - spacing)
        }

        return (items, CGSize(width: width, height: cursor.y + rowHeight))
    }
}
