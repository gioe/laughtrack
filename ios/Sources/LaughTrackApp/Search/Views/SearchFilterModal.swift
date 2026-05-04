import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct PrimitiveSearchControls: View {
    @Binding var sort: PrimitiveSortOption
    let filterCount: Int
    let openFilters: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Menu {
                Picker("Sort", selection: $sort) {
                    ForEach(PrimitiveSortOption.allCases) { option in
                        Text(option.title).tag(option)
                    }
                }
            } label: {
                LaughTrackBrowseChip(
                    "Sort: \(sort.title)",
                    systemImage: "arrow.up.arrow.down",
                    tone: .neutral
                )
            }

            Button(action: openFilters) {
                LaughTrackBrowseChip("\(filterCount) filter\(filterCount == 1 ? "" : "s")", tone: .accent)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Filter results")

            Spacer(minLength: 0)
        }
    }
}

struct SearchFilterModal: View {
    @Environment(\.appTheme) private var theme

    let filters: [Components.Schemas.Filter]
    let total: Int
    @Binding var selectedSlugs: Set<String>
    @Binding var isPresented: Bool
    @State private var draftSlugs: Set<String> = []

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            Color.black.opacity(0.28)
                .ignoresSafeArea()
                .onTapGesture(perform: cancel)

            VStack(alignment: .leading, spacing: theme.spacing.lg) {
                HStack(alignment: .top, spacing: theme.spacing.md) {
                    VStack(alignment: .leading, spacing: theme.spacing.xs) {
                        Text("Filter Results")
                            .font(laughTrack.typography.cardTitle)
                            .foregroundStyle(laughTrack.colors.textPrimary)

                        Text("Select options to refine search.")
                            .font(laughTrack.typography.body)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                    }

                    Spacer(minLength: 0)

                    Button(action: cancel) {
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

                if filters.isEmpty {
                    LaughTrackContextRow(
                        leading: "No filters available",
                        trailing: ""
                    )
                } else {
                    VStack(alignment: .leading, spacing: theme.spacing.md) {
                        Text("Filter By")
                            .font(laughTrack.typography.eyebrow)
                            .foregroundStyle(laughTrack.colors.textSecondary)
                            .textCase(.uppercase)

                        FlowLayout(spacing: theme.spacing.sm, rowSpacing: theme.spacing.sm) {
                            ForEach(filters, id: \.slug) { filter in
                                Button {
                                    toggle(filter.slug)
                                } label: {
                                    LaughTrackBrowseChip(
                                        filter.name,
                                        tone: draftSlugs.contains(filter.slug) ? .selected : .neutral
                                    )
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }

                LaughTrackButton("Show \(total.formatted()) Results", systemImage: "checkmark", density: .compact) {
                    selectedSlugs = draftSlugs
                    isPresented = false
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
        .onAppear {
            draftSlugs = selectedSlugs
        }
    }

    private func toggle(_ slug: String) {
        if draftSlugs.contains(slug) {
            draftSlugs.remove(slug)
        } else {
            draftSlugs.insert(slug)
        }
    }

    private func cancel() {
        draftSlugs = selectedSlugs
        isPresented = false
    }
}

private struct FlowLayout: Layout {
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
