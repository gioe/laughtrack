import Foundation

struct ShowDateStack: Equatable {
    var weekday: String
    var day: String
    var time: String
}

enum ShowFormatting {
    private static let apiFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    static func listDate(_ date: Date, timezoneID: String? = nil) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        if let timezoneID, let timezone = TimeZone(identifier: timezoneID) {
            formatter.timeZone = timezone
        }
        return formatter.string(from: date)
    }

    static func dateStack(_ date: Date, timezoneID: String? = nil) -> ShowDateStack {
        let resolvedTimezone = timezoneID.flatMap(TimeZone.init(identifier:))

        let weekdayFormatter = DateFormatter()
        weekdayFormatter.locale = Locale(identifier: "en_US_POSIX")
        weekdayFormatter.dateFormat = "EEE"
        if let resolvedTimezone {
            weekdayFormatter.timeZone = resolvedTimezone
        }

        let dayFormatter = DateFormatter()
        dayFormatter.locale = Locale(identifier: "en_US_POSIX")
        dayFormatter.dateFormat = "d"
        if let resolvedTimezone {
            dayFormatter.timeZone = resolvedTimezone
        }

        let timeFormatter = DateFormatter()
        timeFormatter.timeStyle = .short
        if let resolvedTimezone {
            timeFormatter.timeZone = resolvedTimezone
        }

        return ShowDateStack(
            weekday: weekdayFormatter.string(from: date).uppercased(),
            day: dayFormatter.string(from: date),
            time: timeFormatter.string(from: date)
        )
    }

    static func isOpenMic(_ name: String?) -> Bool {
        guard let lowered = name?.lowercased() else { return false }
        if lowered.contains("open mic") { return true }
        if lowered.contains("open-mic") { return true }
        return false
    }

    static func apiDate(_ date: Date) -> String {
        apiFormatter.string(from: date)
    }

    static func detailDate(_ date: Date, timezoneID: String?) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .full
        formatter.timeStyle = .short
        if let timezoneID, let timezone = TimeZone(identifier: timezoneID) {
            formatter.timeZone = timezone
        }
        return formatter.string(from: date)
    }

    static func distance(_ miles: Double?) -> String? {
        guard let miles else { return nil }
        return String(format: "%.1f miles away", miles)
    }
}

enum FavoriteFeedback {
    static func message(for name: String, isFavorite: Bool) -> String {
        isFavorite ? "Saved \(name) to favorites." : "Removed \(name) from favorites."
    }
}
