import Foundation
import LaughTrackAPIClient

enum NotificationSortOption: String, CaseIterable, Identifiable {
    case recentlySent
    case upcomingShow
    case unreadFirst

    var id: String { rawValue }

    var title: String {
        switch self {
        case .recentlySent:
            return "Recent"
        case .upcomingShow:
            return "Upcoming"
        case .unreadFirst:
            return "Unread"
        }
    }

    func sorted(_ items: [NotificationCenterItem]) -> [NotificationCenterItem] {
        items.sorted { lhs, rhs in
            switch self {
            case .recentlySent:
                return Self.compareBySentAtThenShowDate(lhs, rhs)
            case .upcomingShow:
                return Self.compareByShowDateThenSentAt(lhs, rhs)
            case .unreadFirst:
                if lhs.isUnread != rhs.isUnread {
                    return lhs.isUnread && !rhs.isUnread
                }
                return Self.compareBySentAtThenShowDate(lhs, rhs)
            }
        }
    }

    private static func compareBySentAtThenShowDate(
        _ lhs: NotificationCenterItem,
        _ rhs: NotificationCenterItem
    ) -> Bool {
        switch compareDescending(lhs.sentAt, rhs.sentAt) {
        case .orderedAscending:
            return true
        case .orderedDescending:
            return false
        case .orderedSame:
            return compareByShowDateThenId(lhs, rhs)
        }
    }

    private static func compareByShowDateThenSentAt(
        _ lhs: NotificationCenterItem,
        _ rhs: NotificationCenterItem
    ) -> Bool {
        switch compareAscending(lhs.showDate, rhs.showDate) {
        case .orderedAscending:
            return true
        case .orderedDescending:
            return false
        case .orderedSame:
            switch compareDescending(lhs.sentAt, rhs.sentAt) {
            case .orderedAscending:
                return true
            case .orderedDescending:
                return false
            case .orderedSame:
                return lhs.id < rhs.id
            }
        }
    }

    private static func compareByShowDateThenId(
        _ lhs: NotificationCenterItem,
        _ rhs: NotificationCenterItem
    ) -> Bool {
        switch compareAscending(lhs.showDate, rhs.showDate) {
        case .orderedAscending:
            return true
        case .orderedDescending:
            return false
        case .orderedSame:
            return lhs.id < rhs.id
        }
    }

    private static func compareAscending(_ lhs: Date?, _ rhs: Date?) -> ComparisonResult {
        switch (lhs, rhs) {
        case let (lhs?, rhs?):
            return lhs.compare(rhs)
        case (.some, nil):
            return .orderedAscending
        case (nil, .some):
            return .orderedDescending
        case (nil, nil):
            return .orderedSame
        }
    }

    private static func compareDescending(_ lhs: Date?, _ rhs: Date?) -> ComparisonResult {
        switch (lhs, rhs) {
        case let (lhs?, rhs?):
            return rhs.compare(lhs)
        case (.some, nil):
            return .orderedAscending
        case (nil, .some):
            return .orderedDescending
        case (nil, nil):
            return .orderedSame
        }
    }
}

/// One row in the notification center, mapped from the generated
/// `NotificationItem`. The model owns the API mapping so the view stays
/// rendering-only and the mapping is unit-testable without hosting any SwiftUI.
struct NotificationCenterItem: Identifiable, Equatable {
    /// Where tapping the row navigates. A single-show entry opens that show; a
    /// grouped entry opens the Favorites tab, which lists the entry's shows.
    enum Tap: Equatable {
        case show(Int)
        case favorites
    }

    let id: String
    let title: String
    let body: String
    let tap: Tap
    let channels: [String]
    let comedianImageURL: URL?
    /// Soonest show date in the entry; drives the "upcoming show" sort.
    let showDate: Date?
    /// True when at least one show in the entry is still upcoming (or undated).
    let hasUpcomingShow: Bool
    /// Parsed from the ISO-8601 `sentAt`; nil if it could not be parsed.
    let sentAt: Date?
    let isUnread: Bool

    init(item: Components.Schemas.NotificationItem) {
        id = item.id
        title = item.title
        body = item.body
        channels = item.channels
        comedianImageURL = URL.normalizedExternalURL(item.comedianImageUrl)

        // shows are soonest-first per the API contract.
        let showDates = item.shows.map { NotificationCenterItem.parseTimestamp($0.showDate ?? "") }
        showDate = showDates.compactMap { $0 }.first
        let now = Date()
        hasUpcomingShow =
            item.shows.isEmpty
            || showDates.contains { date in
                guard let date else { return true }  // undated → keep
                return date > now
            }

        sentAt = NotificationCenterItem.parseTimestamp(item.sentAt)
        isUnread = item.isUnread

        // Grouped entries route to Favorites; single-show entries open the show.
        // showId is still the older-client fallback but here we prefer `route`.
        if item.route == "favorites" {
            tap = .favorites
        } else if let firstShow = item.shows.first {
            tap = .show(firstShow.showId)
        } else {
            tap = .favorites
        }
    }

    /// Test/preview convenience initializer.
    init(
        id: String,
        title: String,
        body: String,
        tap: Tap,
        channels: [String],
        comedianImageURL: URL? = nil,
        showDate: Date? = nil,
        hasUpcomingShow: Bool = true,
        sentAt: Date?,
        isUnread: Bool
    ) {
        self.id = id
        self.title = title
        self.body = body
        self.tap = tap
        self.channels = channels
        self.comedianImageURL = comedianImageURL
        self.showDate = showDate
        self.hasUpcomingShow = hasUpcomingShow
        self.sentAt = sentAt
        self.isUnread = isUnread
    }

    func markedRead() -> NotificationCenterItem {
        NotificationCenterItem(
            id: id,
            title: title,
            body: body,
            tap: tap,
            channels: channels,
            comedianImageURL: comedianImageURL,
            showDate: showDate,
            hasUpcomingShow: hasUpcomingShow,
            sentAt: sentAt,
            isUnread: false
        )
    }

    func metadataLabels(relativeSentAt: String?) -> [String] {
        guard let relativeSentAt else { return [] }
        return [relativeSentAt]
    }

    private static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoFormatterNoFraction = ISO8601DateFormatter()

    static func parseTimestamp(_ raw: String) -> Date? {
        isoFormatter.date(from: raw) ?? isoFormatterNoFraction.date(from: raw)
    }
}

@MainActor
final class NotificationCenterModel: ObservableObject {
    enum Phase: Equatable {
        case idle
        case loading
        /// Loaded successfully; an empty array drives the empty state.
        case loaded([NotificationCenterItem])
        case failure(String)
    }

    @Published private(set) var phase: Phase = .idle
    @Published private(set) var unreadCount: Int = 0
    @Published var sort: NotificationSortOption = .recentlySent

    var sortedItems: [NotificationCenterItem] {
        guard case .loaded(let items) = phase else { return [] }
        return sort.sorted(items)
    }

    func loadIfNeeded(apiClient: Client) async {
        if case .idle = phase {
            await reload(apiClient: apiClient)
        }
    }

    func reload(apiClient: Client) async {
        phase = .loading
        do {
            let output = try await apiClient.getMeNotifications(.init())
            switch output {
            case .ok(let ok):
                let response = try ok.body.json
                let items = response.data.items
                    .map(NotificationCenterItem.init(item:))
                    .filter(\.hasUpcomingShow)
                unreadCount = items.filter(\.isUnread).count
                phase = .loaded(items)
            case .unauthorized, .unprocessableContent:
                phase = .failure("Sign in to see your notifications.")
            case .tooManyRequests:
                phase = .failure(
                    "LaughTrack is rate-limiting notifications right now. Try again shortly."
                )
            case .undocumented(let statusCode, _):
                phase = .failure("LaughTrack couldn't load notifications (status \(statusCode)).")
            }
        } catch {
            phase = .failure(
                "LaughTrack couldn't reach notifications. Check your connection and try again."
            )
        }
    }

    /// Stamp the last-seen high-water mark so the unread badge clears. Returns
    /// `true` on success; the caller refreshes `currentUser` so the launch-time
    /// badge count catches up. Zeroes `unreadCount` for an immediate badge
    /// update but intentionally leaves the loaded rows' `isUnread` flags intact
    /// so the per-row "new" dots stay visible for this viewing session — a
    /// fresh load (next visit) reflects the now-cleared server state.
    @discardableResult
    func markSeen(apiClient: Client) async -> Bool {
        do {
            let output = try await apiClient.markMeNotificationsSeen(.init())
            guard case .ok = output else { return false }
            unreadCount = 0
            return true
        } catch {
            return false
        }
    }
}
