import Foundation
import LaughTrackAPIClient

/// One row in the notification center, mapped from the generated
/// `NotificationItem`. The model owns the API mapping so the view stays
/// rendering-only and the mapping is unit-testable without hosting any SwiftUI.
struct NotificationCenterItem: Identifiable, Equatable {
    let id: String
    let title: String
    let body: String
    let showId: Int
    let channels: [String]
    /// Parsed from the ISO-8601 `sentAt`; nil if it could not be parsed.
    let sentAt: Date?
    let isUnread: Bool

    init(item: Components.Schemas.NotificationItem) {
        id = item.id
        title = item.title
        body = item.body
        showId = item.showId
        channels = item.channels
        sentAt = NotificationCenterItem.parseTimestamp(item.sentAt)
        isUnread = item.isUnread
    }

    /// Test/preview convenience initializer.
    init(
        id: String,
        title: String,
        body: String,
        showId: Int,
        channels: [String],
        sentAt: Date?,
        isUnread: Bool
    ) {
        self.id = id
        self.title = title
        self.body = body
        self.showId = showId
        self.channels = channels
        self.sentAt = sentAt
        self.isUnread = isUnread
    }

    func markedRead() -> NotificationCenterItem {
        NotificationCenterItem(
            id: id,
            title: title,
            body: body,
            showId: showId,
            channels: channels,
            sentAt: sentAt,
            isUnread: false
        )
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
                unreadCount = response.data.unreadCount
                phase = .loaded(response.data.items.map(NotificationCenterItem.init(item:)))
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
    /// `true` on success; the caller refreshes `currentUser` so the
    /// launch-time badge count catches up. Locally flips loaded rows to read
    /// and zeroes `unreadCount` for an immediate UI update.
    @discardableResult
    func markSeen(apiClient: Client) async -> Bool {
        do {
            let output = try await apiClient.markMeNotificationsSeen(.init())
            guard case .ok = output else { return false }
            unreadCount = 0
            if case .loaded(let items) = phase {
                phase = .loaded(items.map { $0.markedRead() })
            }
            return true
        } catch {
            return false
        }
    }
}
