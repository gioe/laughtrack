import SwiftUI
import LaughTrackBridge

struct DateRangeFilterQuickAction: Identifiable {
    let title: String
    let systemImage: String
    let action: () -> Void

    var id: String { title }
}

/// Single sheet used everywhere the app asks the user to pick a date or date
/// range — search-tab date pill, comedian/club detail date filter, week-strip
/// jump pill. Callers bind a `DateRangeFilter`, supply optional show-density
/// data, and get a consistent card-chrome sheet in return.
///
/// Single-day selections are expressed as `from == to`; the underlying
/// `MonthCalendarView` runs in range mode and degenerate-range selections are
/// handled by `MonthCalendarView.rangeSelection`.
///
/// `showsByDate` paints density dots on days with shows; pass `[:]` when the
/// caller has no per-day count handy. `onApply` fires after the binding is
/// updated so callers can mark the filter as active or kick off side effects.
struct DateRangeFilterSheet: View {
    @Binding var filter: DateRangeFilter
    @Binding var isPresented: Bool
    var title: String
    var subtitle: String
    var showsByDate: [Date: Int]
    var minimumDate: Date?
    var todayTitle: String
    var quickActions: [DateRangeFilterQuickAction]
    var onApply: ((DateRangeFilter) -> Void)?
    var onDisplayedMonthChange: ((Date) -> Void)?

    @Environment(\.appTheme) private var theme
    @State private var draftFrom: Date
    @State private var draftTo: Date

    init(
        filter: Binding<DateRangeFilter>,
        isPresented: Binding<Bool>,
        title: String = "Date range",
        subtitle: String = "Choose the show dates to include.",
        showsByDate: [Date: Int] = [:],
        minimumDate: Date? = nil,
        todayTitle: String = "Today",
        quickActions: [DateRangeFilterQuickAction] = [],
        onApply: ((DateRangeFilter) -> Void)? = nil,
        onDisplayedMonthChange: ((Date) -> Void)? = nil
    ) {
        _filter = filter
        _isPresented = isPresented
        self.title = title
        self.subtitle = subtitle
        self.showsByDate = showsByDate
        self.minimumDate = minimumDate
        self.todayTitle = todayTitle
        self.quickActions = quickActions
        self.onApply = onApply
        self.onDisplayedMonthChange = onDisplayedMonthChange

        let calendar = Calendar.current
        let f = calendar.startOfDay(for: filter.wrappedValue.from)
        let t = calendar.startOfDay(for: max(filter.wrappedValue.to, filter.wrappedValue.from))
        _draftFrom = State(initialValue: f)
        _draftTo = State(initialValue: t)
    }

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(alignment: .leading, spacing: theme.spacing.lg) {
            HStack(alignment: .top, spacing: theme.spacing.md) {
                VStack(alignment: .leading, spacing: theme.spacing.xs) {
                    Text(title)
                        .font(laughTrack.typography.cardTitle)
                        .foregroundStyle(laughTrack.colors.textPrimary)

                    Text(subtitle)
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

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: theme.spacing.sm) {
                    LaughTrackButton(
                        "Any date",
                        systemImage: "calendar.badge.minus",
                        tone: .tertiary,
                        density: .compact,
                        fullWidth: false
                    ) {
                        filter.isActive = false
                        onApply?(filter)
                        isPresented = false
                    }

                    LaughTrackButton(
                        todayTitle,
                        systemImage: "calendar",
                        tone: .secondary,
                        density: .compact,
                        fullWidth: false
                    ) {
                        let today = Calendar.current.startOfDay(for: Date())
                        draftFrom = today
                        draftTo = today
                        apply()
                    }

                    ForEach(quickActions) { quickAction in
                        LaughTrackButton(
                            quickAction.title,
                            systemImage: quickAction.systemImage,
                            tone: .secondary,
                            density: .compact,
                            fullWidth: false
                        ) {
                            quickAction.action()
                            isPresented = false
                        }
                    }
                }
            }

            ScrollView {
                MonthCalendarView(
                    selection: .range(
                        start: $draftFrom,
                        end: Binding(
                            get: { max(draftTo, draftFrom) },
                            set: { draftTo = max($0, draftFrom) }
                        )
                    ),
                    showsByDate: showsByDate,
                    minimumDate: minimumDate,
                    onDisplayedMonthChange: onDisplayedMonthChange
                )
                .padding(.horizontal, theme.spacing.xs)
            }
            .font(laughTrack.typography.body)

            HStack(spacing: theme.spacing.sm) {
                Spacer(minLength: 0)

                LaughTrackButton(
                    "Apply",
                    systemImage: "checkmark",
                    density: .compact,
                    fullWidth: false
                ) {
                    apply()
                }
            }
        }
        .padding(theme.spacing.xl)
        .frame(maxWidth: .infinity, alignment: .leading)
        .presentationDetents([.medium, .large])
    }

    private func apply() {
        filter.from = draftFrom
        filter.to = max(draftTo, draftFrom)
        filter.isActive = true
        onApply?(filter)
        isPresented = false
    }
}
