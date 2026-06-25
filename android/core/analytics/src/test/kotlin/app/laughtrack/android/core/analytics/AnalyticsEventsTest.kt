package app.laughtrack.android.core.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pins the cross-client event/parameter/user-property strings to their iOS values
 * (PushAnalyticsEvents / NotificationsAnalyticsEvents / AppBootstrap user props).
 * A rename on either client breaks dashboards silently; this test is the lockstep.
 */
class AnalyticsEventsTest {
    @Test
    fun `push events mirror the iOS catalog`() {
        assertEquals("push_soft_prompt_shown", AnalyticsEvents.Push.SOFT_PROMPT_SHOWN)
        assertEquals("push_soft_prompt_enable_tapped", AnalyticsEvents.Push.SOFT_PROMPT_ENABLE_TAPPED)
        assertEquals("push_soft_prompt_defer_tapped", AnalyticsEvents.Push.SOFT_PROMPT_DEFER_TAPPED)
        assertEquals("push_os_prompt_result", AnalyticsEvents.Push.OS_PROMPT_RESULT)
        assertEquals("push_settings_toggle_changed", AnalyticsEvents.Push.SETTINGS_TOGGLE_CHANGED)
        assertEquals("trigger", AnalyticsEvents.Push.Param.TRIGGER)
        assertEquals("deferral_count", AnalyticsEvents.Push.Param.DEFERRAL_COUNT)
        assertEquals("granted", AnalyticsEvents.Push.Param.GRANTED)
        assertEquals("from_denied_state", AnalyticsEvents.Push.Param.FROM_DENIED_STATE)
        assertEquals("engagement_moment", AnalyticsEvents.Push.Trigger.ENGAGEMENT_MOMENT)
        assertEquals("settings_toggle", AnalyticsEvents.Push.Trigger.SETTINGS_TOGGLE)
    }

    @Test
    fun `notification events mirror the iOS catalog`() {
        assertEquals("notifications_viewed", AnalyticsEvents.Notifications.VIEWED)
        assertEquals("notification_card_tapped", AnalyticsEvents.Notifications.CARD_TAPPED)
        assertEquals("unread_count", AnalyticsEvents.Notifications.Param.UNREAD_COUNT)
        assertEquals("show_id", AnalyticsEvents.Notifications.Param.SHOW_ID)
    }

    @Test
    fun `user property keys mirror the iOS app bootstrap`() {
        assertEquals("comedian_onboarding_completed", AnalyticsUserProperties.COMEDIAN_ONBOARDING_COMPLETED)
        assertEquals("has_zip", AnalyticsUserProperties.HAS_ZIP)
    }

    @Test
    fun `every event name is snake_case and within Firebase's 40-char cap`() {
        val names =
            listOf(
                AnalyticsEvents.Push.SOFT_PROMPT_SHOWN,
                AnalyticsEvents.Push.SOFT_PROMPT_ENABLE_TAPPED,
                AnalyticsEvents.Push.SOFT_PROMPT_DEFER_TAPPED,
                AnalyticsEvents.Push.OS_PROMPT_RESULT,
                AnalyticsEvents.Push.SETTINGS_TOGGLE_CHANGED,
                AnalyticsEvents.Notifications.VIEWED,
                AnalyticsEvents.Notifications.CARD_TAPPED,
                AnalyticsEvents.Onboarding.COMPLETED,
                AnalyticsEvents.Search.PERFORMED,
                AnalyticsEvents.Cards.TAPPED,
            )
        val snakeCase = Regex("^[a-z][a-z0-9_]*$")
        names.forEach { name ->
            assertTrue("'$name' is not snake_case", snakeCase.matches(name))
            assertTrue("'$name' exceeds 40 chars", name.length <= 40)
        }
    }
}
