import Foundation

/// Event names and parameter keys for the notification center.
///
/// Centralizing the strings keeps emissions and assertions in lockstep — one
/// rename here propagates to every callsite and every test. Every name follows
/// the snake_case `<feature>_<action>` convention documented in `ios/CLAUDE.md`
/// and stays under the 40-character cap Firebase enforces on event names and
/// parameter keys. Parameter values are restricted to String/Int/Double/Bool.
public enum NotificationsAnalyticsEvents {
    /// Emitted when the notification center opens and its feed has loaded
    /// (fired alongside the mark-seen call, not on a failed/empty-never-loaded
    /// fetch). Carries `unread_count` so the funnel can relate opens to how
    /// many unread items were waiting.
    public static let viewed = "notifications_viewed"
    /// Emitted when the user taps a notification row, which deep-links to the
    /// show. Carries `show_id` for attribution.
    public static let cardTapped = "notification_card_tapped"

    public enum Param {
        public static let unreadCount = "unread_count"
        public static let showId = "show_id"
    }
}
