import Foundation

/// Event names and parameter keys for the push-permission funnel.
///
/// Centralizing the strings keeps emissions and assertions in lockstep — one
/// rename here propagates to every callsite and every test. Every name follows
/// the snake_case `<feature>_<action>` convention documented in
/// `ios/CLAUDE.md` and stays under the 40-character cap Firebase enforces on
/// event names and parameter keys.
public enum PushAnalyticsEvents {
    /// Emitted when the soft prompt sheet is presented to the user.
    public static let softPromptShown = "push_soft_prompt_shown"
    /// Emitted when the user taps the Enable button on the soft prompt sheet.
    ///
    /// Semantically a "user intent" signal — fires on every tap regardless of
    /// the underlying OS status, because the funnel question is "how many
    /// users tapped Enable", not "how many OS dialogs were shown". When the
    /// status is already `.authorized` or `.denied`, no OS dialog appears and
    /// no `osPromptResult` event follows; the per-step ratio
    /// `enable_tapped : os_prompt_result` is therefore expected to be ≥ 1:1,
    /// not exactly 1:1. Funnel queries that join on a 1:1 assumption will
    /// undercount the already-authorized branch.
    public static let softPromptEnableTapped = "push_soft_prompt_enable_tapped"
    /// Emitted when the user taps the Maybe-later button on the soft prompt sheet.
    public static let softPromptDeferTapped = "push_soft_prompt_defer_tapped"
    /// Emitted after the OS push-authorization dialog resolves, regardless of
    /// the callsite that surfaced it (soft prompt, onboarding, or settings).
    public static let osPromptResult = "push_os_prompt_result"
    /// Emitted when the Settings notification toggle is flipped.
    ///
    /// Fires for both enable=true and enable=false transitions; the
    /// `from_denied_state` parameter is included on both paths and reflects
    /// "has this user previously encountered the OS-denied alert in this
    /// model's lifetime" — a session-level recovery-context signal that's
    /// useful on either direction (e.g. "of users who later disabled push,
    /// how many had previously had to recover from a denied state"). It is
    /// not gated to enable=true.
    public static let settingsToggleChanged = "push_settings_toggle_changed"

    public enum Param {
        public static let trigger = "trigger"
        public static let deferralCount = "deferral_count"
        public static let granted = "granted"
        public static let enabled = "enabled"
        public static let fromDeniedState = "from_denied_state"
    }

    /// Identifies which UI surface initiated the OS push-authorization dialog.
    public enum Trigger: String {
        case engagementMoment = "engagement_moment"
        case onboarding
        case settingsToggle = "settings_toggle"
    }
}
