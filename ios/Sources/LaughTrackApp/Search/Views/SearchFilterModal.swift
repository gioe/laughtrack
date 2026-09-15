import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct SearchFilterModal: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    let filters: [Components.Schemas.Filter]
    /// Live result count — comes from `model.phase.total` at the call site and
    /// re-renders the modal each time the underlying search refetches.
    let total: Int
    @Binding var selectedSlugs: Set<String>
    @Binding var isPresented: Bool
    var maximumPrice: Binding<ShowMaximumPriceOption>? = nil

    /// Snapshot of `selectedSlugs` taken when the sheet first appears, so
    /// dismiss-without-commit (X tap or drag-down) can restore the user's
    /// original selection. Toggling chips writes through to `selectedSlugs`
    /// directly, which triggers the parent view's existing `.task(id:)` to
    /// refetch and update `total` — that's what makes the "Show N results"
    /// label live-update as the user experiments.
    @State private var initialSlugs: Set<String> = []
    @State private var didCommit = false
    @State private var initialMaximumPrice: ShowMaximumPriceOption = .any

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

                        Text(maximumPrice == nil
                             ? "Tap a tag to add or remove it. The result count updates live."
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
                        if let maximumPrice {
                            Text("Maximum price")
                                .font(laughTrack.typography.metadata.weight(.semibold))
                                .foregroundStyle(laughTrack.colors.textSecondary)
                            Picker("Maximum price", selection: maximumPrice) {
                                ForEach(ShowMaximumPriceOption.allCases) { option in
                                    Text(option.title).tag(option)
                                }
                            }
                            .pickerStyle(.menu)
                            .tint(laughTrack.colors.accentStrong)
                            .frame(minHeight: 44)
                            .accessibilityLabel("Maximum price")
                        }

                        if filters.isEmpty {
                            if maximumPrice == nil {
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

                VStack(spacing: theme.spacing.sm) {
                    Button {
                        didCommit = true
                        isPresented = false
                    } label: {
                        HStack(spacing: 8) {
                            Text("Show \(total.formatted()) results".uppercased())
                                .font(.system(size: 13, weight: .heavy, design: .rounded))
                                .tracking(1.2)
                                .contentTransition(.numericText())
                                .animation(.easeOut(duration: 0.2), value: total)
                            Image(systemName: "arrow.right")
                                .font(.system(size: 12, weight: .bold))
                        }
                        .foregroundStyle(Color.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .frame(minHeight: 44)
                        .background(laughTrack.colors.accentStrong)
                        .clipShape(Capsule(style: .continuous))
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.45), radius: 8, y: 3)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Show \(total.formatted()) results")

                    Button {
                        selectedSlugs = []
                        maximumPrice?.wrappedValue = .any
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
                        ? (maximumPrice == nil ? "Clears the selected filters." : "Clears the selected filters and price limit.")
                        : "No filters are currently applied.")
                }

                Spacer(minLength: 0)
            }
            .padding(.horizontal, theme.spacing.xl)
            .padding(.top, theme.spacing.xl)
            .padding(.bottom, theme.spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(LaughTrackAtmosphereBackground())
        .onAppear {
            initialSlugs = selectedSlugs
            initialMaximumPrice = maximumPrice?.wrappedValue ?? .any
            didCommit = false
        }
        .onDisappear {
            // Drag-to-dismiss bypasses `cancel()`, so re-apply the snapshot
            // here whenever the sheet closes without an explicit commit. No-op
            // when the user already confirmed via the action button.
            if !didCommit {
                restoreInitialSelection()
            }
        }
    }

    private var filterChips: some View {
        ForEach(filters, id: \.slug) { filter in
            FilterMarqueeChip(
                title: filter.name,
                isSelected: selectedSlugs.contains(filter.slug)
            ) {
                toggle(filter.slug)
            }
        }
    }

    private func toggle(_ slug: String) {
        if selectedSlugs.contains(slug) {
            selectedSlugs.remove(slug)
        } else {
            selectedSlugs.insert(slug)
        }
    }

    private var hasActiveFilters: Bool {
        !selectedSlugs.isEmpty || (maximumPrice?.wrappedValue ?? .any) != .any
    }

    private func restoreInitialSelection() {
        if selectedSlugs != initialSlugs { selectedSlugs = initialSlugs }
        if let maximumPrice, maximumPrice.wrappedValue != initialMaximumPrice {
            maximumPrice.wrappedValue = initialMaximumPrice
        }
    }

    private func cancel() {
        restoreInitialSelection()
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
        layout(in: proposal.width ?? 0, subviews: subviews).size
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

    private func layout(in maxWidth: CGFloat, subviews: Subviews) -> (items: [(index: Int, frame: CGRect)], size: CGSize) {
        var items: [(index: Int, frame: CGRect)] = []
        var cursor = CGPoint.zero
        var rowHeight: CGFloat = 0
        var width: CGFloat = 0

        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            if cursor.x > 0, maxWidth > 0, cursor.x + size.width > maxWidth {
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
