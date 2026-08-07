package app.laughtrack.android.core.analytics

/**
 * The analytics event/parameter catalog. Names follow the snake_case
 * `<feature>_<action>` convention and stay under Firebase's 40-char cap.
 *
 * [Push] and [Notifications] mirror the iOS catalog VERBATIM (PushAnalyticsEvents
 * / NotificationsAnalyticsEvents) so dashboards stay cross-client comparable —
 * RelativeTime-style unit tests pin the exact strings. [Discover] also mirrors
 * iOS, while [Onboarding], [Search], and [Cards] are Android-leading events for
 * flows iOS has not instrumented yet.
 */
object AnalyticsEvents {
    /** Push-permission funnel — mirrors iOS PushAnalyticsEvents exactly. */
    object Push {
        const val SOFT_PROMPT_SHOWN = "push_soft_prompt_shown"
        const val SOFT_PROMPT_ENABLE_TAPPED = "push_soft_prompt_enable_tapped"
        const val SOFT_PROMPT_DEFER_TAPPED = "push_soft_prompt_defer_tapped"
        const val OS_PROMPT_RESULT = "push_os_prompt_result"
        const val SETTINGS_TOGGLE_CHANGED = "push_settings_toggle_changed"

        object Param {
            const val TRIGGER = "trigger"
            const val DEFERRAL_COUNT = "deferral_count"
            const val GRANTED = "granted"
            const val ENABLED = "enabled"
            const val FROM_DENIED_STATE = "from_denied_state"
        }

        object Trigger {
            const val ENGAGEMENT_MOMENT = "engagement_moment"
            const val ONBOARDING = "onboarding"
            const val SETTINGS_TOGGLE = "settings_toggle"
        }
    }

    /** Notification center — mirrors iOS NotificationsAnalyticsEvents exactly. */
    object Notifications {
        const val VIEWED = "notifications_viewed"
        const val CARD_TAPPED = "notification_card_tapped"

        object Param {
            const val UNREAD_COUNT = "unread_count"
            const val SHOW_ID = "show_id"
        }
    }

    /** Comedian onboarding (Android-leading). */
    object Onboarding {
        const val COMPLETED = "onboarding_completed"
    }

    /** Search (Android-leading). */
    object Search {
        const val PERFORMED = "search_performed"

        object Param {
            const val PIVOT = "pivot"
        }
    }

    /** Entity-card taps from list surfaces (Android-leading). */
    object Cards {
        const val TAPPED = "card_tapped"

        object Param {
            const val ENTITY_TYPE = "entity_type"
            const val ENTITY_ID = "entity_id"
        }
    }

    /** Server-directed Discover rail interactions — mirrors iOS exactly. */
    object Discover {
        const val RAIL_SELECTED = "discover_rail_selected"

        object Param {
            const val RAIL_KEY = "rail_key"
            const val POLICY_VERSION = "policy_version"
            const val RANK = "rank"
        }
    }
}

/** User/cohort property keys — mirror iOS AppBootstrap setUserProperty keys exactly. */
object AnalyticsUserProperties {
    const val COMEDIAN_ONBOARDING_COMPLETED = "comedian_onboarding_completed"
    const val HAS_ZIP = "has_zip"
}
