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

    private static let weekdayStackFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "EEE"
        return formatter
    }()

    private static let dayStackFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "d"
        return formatter
    }()

    private static let timeStackFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
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
        let resolvedTimezone = timezoneID.flatMap(TimeZone.init(identifier:)) ?? TimeZone.current

        weekdayStackFormatter.timeZone = resolvedTimezone
        dayStackFormatter.timeZone = resolvedTimezone
        timeStackFormatter.timeZone = resolvedTimezone

        return ShowDateStack(
            weekday: weekdayStackFormatter.string(from: date).uppercased(),
            day: dayStackFormatter.string(from: date),
            time: timeStackFormatter.string(from: date)
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

    /// Treat the show as live from start through this many seconds after — covers a
    /// typical standup set plus a buffer for late starts.
    private static let liveWindow: TimeInterval = 2.5 * 60 * 60

    enum ShowCountdownTone {
        case future
        case live
        case past
    }

    struct ShowCountdown: Equatable {
        let label: String
        let tone: ShowCountdownTone
    }

    static func countdown(for showDate: Date, now: Date = Date()) -> ShowCountdown {
        let diff = showDate.timeIntervalSince(now)
        if diff <= 0, diff > -liveWindow {
            return ShowCountdown(label: "Happening now", tone: .live)
        }
        if diff > 0 {
            return ShowCountdown(label: "Show in \(relativeFuture(diff))", tone: .future)
        }
        return ShowCountdown(label: "Ended \(relativePast(-diff)) ago", tone: .past)
    }

    // Floor for both directions so the unit only flips when the boundary is
    // crossed and a 14-month-out show renders symmetrically with a 14-month-ago
    // show.
    private static func relativeFuture(_ seconds: TimeInterval) -> String {
        let minutes = Int(seconds / 60)
        if minutes < 60 {
            return "\(minutes) \(minutes == 1 ? "minute" : "minutes")"
        }
        let hours = Int(seconds / 3600)
        if hours < 24 {
            return "\(hours) \(hours == 1 ? "hour" : "hours")"
        }
        let days = Int(seconds / 86_400)
        if days < 14 {
            return "\(days) \(days == 1 ? "day" : "days")"
        }
        let weeks = days / 7
        if weeks < 9 {
            return "\(weeks) \(weeks == 1 ? "week" : "weeks")"
        }
        let months = days / 30
        if months < 12 {
            return "\(months) \(months == 1 ? "month" : "months")"
        }
        let years = days / 365
        return "\(years) \(years == 1 ? "year" : "years")"
    }

    private static func relativePast(_ seconds: TimeInterval) -> String {
        let minutes = Int(seconds / 60)
        if minutes < 60 {
            return "\(minutes) \(minutes == 1 ? "minute" : "minutes")"
        }
        let hours = Int(seconds / 3600)
        if hours < 24 {
            return "\(hours) \(hours == 1 ? "hour" : "hours")"
        }
        let days = Int(seconds / 86_400)
        if days < 14 {
            return "\(days) \(days == 1 ? "day" : "days")"
        }
        let weeks = days / 7
        if weeks < 9 {
            return "\(weeks) \(weeks == 1 ? "week" : "weeks")"
        }
        let months = days / 30
        if months < 12 {
            return "\(months) \(months == 1 ? "month" : "months")"
        }
        let years = days / 365
        return "\(years) \(years == 1 ? "year" : "years")"
    }
}

enum FavoriteFeedback {
    static func message(for name: String, isFavorite: Bool) -> String {
        isFavorite ? "Saved \(name) to favorites." : "Removed \(name) from favorites."
    }
}
