import Foundation

/// Shared state shape for every "pick a date / date range" affordance in the
/// app — the search-tab date pill, comedian/club detail filters, and the
/// week-strip jump pill. Callers bind a `DateRangeFilter` and read whichever
/// fields their query needs.
struct DateRangeFilter: Hashable {
    var from: Date
    var to: Date
    var isActive: Bool

    /// A filter spanning today through today + 90 days. Suitable as the
    /// initial value for any pill: opens on a sensible default range, with
    /// `isActive` controlling whether the filter is applied (caller decides).
    static func defaultUpcoming(
        now: Date = Date(),
        calendar: Calendar = .current,
        activeByDefault: Bool = false
    ) -> DateRangeFilter {
        let today = calendar.startOfDay(for: now)
        let end = calendar.date(byAdding: .day, value: 90, to: today) ?? today
        return DateRangeFilter(from: today, to: end, isActive: activeByDefault)
    }

    /// Label shown on the pill that triggers the picker. Falls back to
    /// "Any date" when inactive, "Today" when the range collapses to today,
    /// a single short date when from == to, or "MMM d - MMM d" otherwise.
    func pillLabel(now: Date = Date(), calendar: Calendar = .current) -> String {
        guard isActive else { return "Any date" }

        let normalizedFrom = calendar.startOfDay(for: from)
        let normalizedTo = calendar.startOfDay(for: max(to, from))
        let today = calendar.startOfDay(for: now)

        if normalizedFrom == today, normalizedTo == today {
            return "Today"
        }
        if normalizedFrom == normalizedTo {
            return Self.shortDateFormatter.string(from: normalizedFrom)
        }
        return "\(Self.shortDateFormatter.string(from: normalizedFrom)) - \(Self.shortDateFormatter.string(from: normalizedTo))"
    }

    private static let shortDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.setLocalizedDateFormatFromTemplate("MMM d")
        return formatter
    }()
}
