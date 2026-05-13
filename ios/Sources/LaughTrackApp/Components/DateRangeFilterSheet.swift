import SwiftUI
import LaughTrackBridge

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
        onApply: ((DateRangeFilter) -> Void)? = nil,
        onDisplayedMonthChange: ((Date) -> Void)? = nil
    ) {
        _filter = filter
        _isPresented = isPresented
        self.title = title
        self.subtitle = subtitle
        self.showsByDate = showsByDate
        self.minimumDate = minimumDate
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
            .frame(maxHeight: 430)

            VStack(spacing: theme.spacing.sm) {
                LaughTrackButton("Apply", systemImage: "checkmark", density: .compact) {
                    apply()
                }

                LaughTrackButton("Today", systemImage: "calendar", tone: .secondary, density: .compact) {
                    let today = Calendar.current.startOfDay(for: Date())
                    draftFrom = today
                    draftTo = today
                    apply()
                }

                LaughTrackButton("Any date", systemImage: "calendar.badge.minus", tone: .tertiary, density: .compact) {
                    filter.isActive = false
                    onApply?(filter)
                    isPresented = false
                }
            }

            Spacer(minLength: 0)
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
