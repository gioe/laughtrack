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
    public static let softPromptEnableTapped = "push_soft_prompt_enable_tapped"
    /// Emitted when the user taps the Maybe-later button on the soft prompt sheet.
    public static let softPromptDeferTapped = "push_soft_prompt_defer_tapped"
    /// Emitted after the OS push-authorization dialog resolves, regardless of
    /// the callsite that surfaced it (soft prompt, onboarding, or settings).
    public static let osPromptResult = "push_os_prompt_result"
    /// Emitted when the Settings notification toggle is flipped.
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
