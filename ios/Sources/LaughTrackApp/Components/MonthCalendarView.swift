import SwiftUI
import LaughTrackBridge

/// Month-grid calendar that replaces the native `DatePicker(.graphical)` in
/// places where we want full visual control — per-day density dots, faded
/// past dates, a today ring, and an accent fill on the selected day(s).
///
/// Pass `selection: .single($date)` for single-date callers. Pass
/// `selection: .range(start: $from, end: $to)` for range callers; range mode
/// behaves as a two-stage picker (first tap inside the grid sets the start
/// and resets the end to match it; the next tap sets the end, swapping
/// endpoints if the user tapped earlier than the current start).
struct MonthCalendarView: View {
    enum Selection {
        case single(Binding<Date>)
        case range(start: Binding<Date>, end: Binding<Date>)
    }

    let selection: Selection
    let showsByDate: [Date: Int]
    let minimumDate: Date?

    @Environment(\.appTheme) private var theme
    @State private var displayedMonth: Date
    @State private var rangeAwaitingEnd: Bool

    init(
        selection: Selection,
        showsByDate: [Date: Int] = [:],
        minimumDate: Date? = nil
    ) {
        self.selection = selection
        self.showsByDate = showsByDate
        self.minimumDate = minimumDate

        let anchor: Date
        let awaitingEnd: Bool
        switch selection {
        case .single(let binding):
            anchor = binding.wrappedValue
            awaitingEnd = false
        case .range(let start, let end):
            anchor = start.wrappedValue
            let calendar = Calendar.current
            awaitingEnd = !calendar.isDate(
                calendar.startOfDay(for: start.wrappedValue),
                inSameDayAs: calendar.startOfDay(for: end.wrappedValue)
            )
        }
        _displayedMonth = State(initialValue: MonthCalendarView.monthStart(for: anchor))
        _rangeAwaitingEnd = State(initialValue: awaitingEnd)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            weekdayRow
            grid
        }
    }

    private var header: some View {
        let laughTrack = theme.laughTrackTokens
        return HStack {
            chevron(systemImage: "chevron.left", direction: -1)
            Spacer(minLength: 0)
            Text(monthTitle)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .accessibilityLabel("Showing \(monthTitle)")
            Spacer(minLength: 0)
            chevron(systemImage: "chevron.right", direction: 1)
        }
    }

    @ViewBuilder
    private func chevron(systemImage: String, direction: Int) -> some View {
        let laughTrack = theme.laughTrackTokens
        let proposed = calendar.date(byAdding: .month, value: direction, to: displayedMonth)
            ?? displayedMonth
        let isDisabled = direction < 0 && isMonthBeforeMinimum(proposed)
        Button {
            displayedMonth = MonthCalendarView.monthStart(for: proposed)
        } label: {
            Image(systemName: systemImage)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(laughTrack.colors.textPrimary)
                .frame(width: 34, height: 34)
                .background(Circle().fill(laughTrack.colors.surfaceElevated))
                .overlay(Circle().stroke(laughTrack.colors.borderSubtle, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.4 : 1)
        .accessibilityLabel(direction < 0 ? "Previous month" : "Next month")
    }

    private var weekdayRow: some View {
        let laughTrack = theme.laughTrackTokens
        return HStack(spacing: 0) {
            ForEach(Array(weekdaySymbols.enumerated()), id: \.offset) { _, symbol in
                Text(symbol)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.textSecondary)
                    .textCase(.uppercase)
                    .frame(maxWidth: .infinity)
            }
        }
    }

    private var grid: some View {
        VStack(spacing: 4) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                HStack(spacing: 0) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, cellDate in
                        cellView(for: cellDate)
                            .frame(maxWidth: .infinity)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func cellView(for date: Date?) -> some View {
        if let date {
            DayCell(
                date: date,
                isToday: calendar.isDate(date, inSameDayAs: today),
                state: state(for: date),
                isPast: isPast(date),
                hasShow: (showsByDate[calendar.startOfDay(for: date)] ?? 0) > 0
            )
            .contentShape(Rectangle())
            .onTapGesture {
                guard !isPast(date) else { return }
                tap(date)
            }
            .accessibilityElement()
            .accessibilityLabel(accessibilityLabel(for: date))
            .accessibilityAddTraits(state(for: date) != .none ? [.isSelected] : [])
        } else {
            Color.clear.frame(height: 44)
        }
    }

    private func state(for date: Date) -> MonthCalendarCellState {
        let day = calendar.startOfDay(for: date)
        switch selection {
        case .single(let binding):
            return calendar.isDate(binding.wrappedValue, inSameDayAs: day) ? .singleSelected : .none
        case .range(let start, let end):
            let s = calendar.startOfDay(for: start.wrappedValue)
            let e = calendar.startOfDay(for: end.wrappedValue)
            if calendar.isDate(s, inSameDayAs: e) && calendar.isDate(day, inSameDayAs: s) {
                return .singleSelected
            }
            if calendar.isDate(day, inSameDayAs: s) { return .rangeStart }
            if calendar.isDate(day, inSameDayAs: e) { return .rangeEnd }
            if day > s && day < e { return .rangeMiddle }
            return .none
        }
    }

    private func tap(_ date: Date) {
        let day = calendar.startOfDay(for: date)
        switch selection {
        case .single(let binding):
            binding.wrappedValue = day
        case .range(let start, let end):
            let result = MonthCalendarView.rangeSelection(
                afterTap: day,
                start: start.wrappedValue,
                end: end.wrappedValue,
                awaitingEnd: rangeAwaitingEnd,
                calendar: calendar
            )
            start.wrappedValue = result.start
            end.wrappedValue = result.end
            rangeAwaitingEnd = result.awaitingEnd
        }
    }

    private func accessibilityLabel(for date: Date) -> String {
        var label = Self.accessibilityDateFormatter.string(from: date)
        if isPast(date) { label += ", unavailable" }
        if (showsByDate[calendar.startOfDay(for: date)] ?? 0) > 0 {
            label += ", has shows"
        }
        return label
    }

    private var calendar: Calendar { Calendar.current }
    private var today: Date { calendar.startOfDay(for: Date()) }

    private var monthTitle: String {
        Self.monthTitleFormatter.string(from: displayedMonth)
    }

    private static let monthTitleFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM yyyy"
        return formatter
    }()

    private static let accessibilityDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .full
        return formatter
    }()

    static let dayNumberFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "d"
        return formatter
    }()

    private var weekdaySymbols: [String] {
        MonthCalendarView.weekdaySymbols(for: calendar)
    }

    private var rows: [[Date?]] {
        MonthCalendarView.rows(for: displayedMonth, calendar: calendar)
    }

    private func isPast(_ date: Date) -> Bool {
        MonthCalendarView.isDate(date, beforeMinimum: minimumDate, calendar: calendar)
    }

    private func isMonthBeforeMinimum(_ candidate: Date) -> Bool {
        MonthCalendarView.isMonth(candidate, beforeMinimum: minimumDate, calendar: calendar)
    }

    static func rangeSelection(
        afterTap date: Date,
        start: Date,
        end: Date,
        awaitingEnd: Bool,
        calendar: Calendar = .current
    ) -> (start: Date, end: Date, awaitingEnd: Bool) {
        let day = calendar.startOfDay(for: date)
        let currentStart = calendar.startOfDay(for: start)
        if awaitingEnd {
            if day < currentStart {
                return (day, currentStart, false)
            }
            return (currentStart, day, false)
        }
        return (day, day, true)
    }

    static func weekdaySymbols(for calendar: Calendar = .current) -> [String] {
        var symbols = calendar.veryShortWeekdaySymbols
        let offset = calendar.firstWeekday - 1
        if offset > 0 {
            symbols = Array(symbols[offset...]) + Array(symbols[..<offset])
        }
        return symbols
    }

    static func rows(for displayedMonth: Date, calendar: Calendar = .current) -> [[Date?]] {
        let firstOfMonth = calendar.dateInterval(of: .month, for: displayedMonth)?.start
            ?? calendar.startOfDay(for: displayedMonth)
        let firstWeekday = calendar.component(.weekday, from: firstOfMonth)
        let daysInMonth = calendar.range(of: .day, in: .month, for: firstOfMonth)?.count ?? 31

        let leadingNils = (firstWeekday - calendar.firstWeekday + 7) % 7

        var cells: [Date?] = Array(repeating: nil, count: leadingNils)
        for offset in 0..<daysInMonth {
            guard let day = calendar.date(byAdding: .day, value: offset, to: firstOfMonth),
                  calendar.isDate(day, equalTo: firstOfMonth, toGranularity: .month) else {
                break
            }
            cells.append(day)
        }
        while cells.count % 7 != 0 || cells.count < 35 {
            cells.append(nil)
        }
        var grouped: [[Date?]] = []
        for row in 0..<(cells.count / 7) {
            grouped.append(Array(cells[row * 7..<row * 7 + 7]))
        }
        while grouped.count > 5, let last = grouped.last, last.allSatisfy({ $0 == nil }) {
            grouped.removeLast()
        }
        return grouped
    }

    static func isMonth(
        _ candidate: Date,
        beforeMinimum minimum: Date?,
        calendar: Calendar = .current
    ) -> Bool {
        guard let minimum else { return false }
        let candidateMonth = MonthCalendarView.monthStart(for: candidate, calendar: calendar)
        let minimumMonth = MonthCalendarView.monthStart(for: minimum, calendar: calendar)
        return candidateMonth < minimumMonth
    }

    static func isDate(
        _ date: Date,
        beforeMinimum minimum: Date?,
        calendar: Calendar = .current
    ) -> Bool {
        guard let minimum else { return false }
        return calendar.startOfDay(for: date) < calendar.startOfDay(for: minimum)
    }

    static func monthStart(for date: Date, calendar: Calendar = .current) -> Date {
        return calendar.dateInterval(of: .month, for: date)?.start ?? calendar.startOfDay(for: date)
    }
}

private enum MonthCalendarCellState {
    case none
    case singleSelected
    case rangeStart
    case rangeEnd
    case rangeMiddle
}

private struct DayCell: View {
    @Environment(\.appTheme) private var theme

    let date: Date
    let isToday: Bool
    let state: MonthCalendarCellState
    let isPast: Bool
    let hasShow: Bool

    var body: some View {
        ZStack {
            background
            VStack(spacing: 2) {
                Text(dayLabel)
                    .font(.system(size: 16, weight: state == .none ? .regular : .semibold))
                    .foregroundStyle(textColor)
                Circle()
                    .fill(dotColor)
                    .frame(width: 4, height: 4)
            }
        }
        .frame(height: 44)
        .opacity(isPast ? 0.35 : 1)
    }

    private var dayLabel: String {
        MonthCalendarView.dayNumberFormatter.string(from: date)
    }

    @ViewBuilder
    private var background: some View {
        let laughTrack = theme.laughTrackTokens
        switch state {
        case .none:
            if isToday {
                Circle()
                    .stroke(laughTrack.colors.accent, lineWidth: 1.5)
                    .frame(width: 34, height: 34)
            } else {
                EmptyView()
            }
        case .singleSelected, .rangeStart, .rangeEnd:
            Circle()
                .fill(laughTrack.colors.accentStrong)
                .frame(width: 34, height: 34)
        case .rangeMiddle:
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(laughTrack.colors.accentMuted.opacity(0.6))
                .frame(height: 34)
        }
    }

    private var textColor: Color {
        let laughTrack = theme.laughTrackTokens
        switch state {
        case .singleSelected, .rangeStart, .rangeEnd:
            return laughTrack.colors.textInverse
        case .rangeMiddle, .none:
            return laughTrack.colors.textPrimary
        }
    }

    private var dotColor: Color {
        guard hasShow else { return .clear }
        let laughTrack = theme.laughTrackTokens
        switch state {
        case .singleSelected, .rangeStart, .rangeEnd:
            return laughTrack.colors.textInverse
        case .rangeMiddle, .none:
            return laughTrack.colors.accentStrong
        }
    }
}
