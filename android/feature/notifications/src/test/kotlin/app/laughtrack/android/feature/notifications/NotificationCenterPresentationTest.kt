package app.laughtrack.android.feature.notifications

import app.laughtrack.android.core.network.generated.model.NotificationComedian
import app.laughtrack.android.core.network.generated.model.NotificationItem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZonedDateTime

class NotificationCenterPresentationTest {
    private val now = ZonedDateTime.parse("2026-07-15T15:00:00-04:00")

    @Test
    fun unreadRowExposesSourceTimestampAndUnreadEmphasis() {
        val presentation =
            notificationRowPresentation(
                item(
                    title = "Taylor Tomlinson has a show near you",
                    body = "The Comedy Cellar on Saturday at 8:00 PM",
                    isUnread = true,
                    sentAt = "2026-07-15T13:00:00-04:00",
                    comedianNames = listOf("Taylor Tomlinson"),
                ),
                now,
            )

        assertEquals("Taylor Tomlinson", presentation.source)
        assertEquals("2h", presentation.relativeTime)
        assertTrue(presentation.isUnread)
        assertEquals("The Comedy Cellar on Saturday at 8:00 PM", presentation.body)
    }

    @Test
    fun readGroupedRowRetainsSourceContextWithoutUnreadEmphasis() {
        val presentation =
            notificationRowPresentation(
                item(
                    title = "Your favorites have 2 new shows",
                    body = "",
                    isUnread = false,
                    sentAt = "2026-07-14T15:00:00-04:00",
                    comedianNames = listOf("Taylor Tomlinson", "Sam Jay"),
                ),
                now,
            )

        assertEquals("Taylor Tomlinson + 1 more", presentation.source)
        assertEquals("1d", presentation.relativeTime)
        assertFalse(presentation.isUnread)
        assertNull(presentation.body)
    }

    @Test
    fun longContentIsPreservedForMultilineLayout() {
        val longTitle =
            "Taylor Tomlinson and several comedians you follow have newly announced shows " +
                "near your favorite venues"
        val longBody =
            "The Comedy Cellar, The Bell House, and Union Hall all added dates across the " +
                "next several weekends in New York."

        val presentation =
            notificationRowPresentation(
                item(
                    title = longTitle,
                    body = longBody,
                    isUnread = true,
                    sentAt = "2026-07-15T14:55:00-04:00",
                    comedianNames = listOf("Taylor Tomlinson"),
                ),
                now,
            )

        assertEquals(longTitle, presentation.title)
        assertEquals(longBody, presentation.body)
        assertEquals("5m", presentation.relativeTime)
    }

    private fun item(
        title: String,
        body: String,
        isUnread: Boolean,
        sentAt: String,
        comedianNames: List<String>,
    ) = NotificationItem(
        id = title,
        title = title,
        body = body,
        comedianName = comedianNames.firstOrNull().orEmpty(),
        comedianImageUrl = "",
        comedians =
            comedianNames.mapIndexed { index, name ->
                NotificationComedian(
                    comedianId = "comedian-$index",
                    comedianName = name,
                    comedianImageUrl = "",
                )
            },
        shows = emptyList(),
        channels = listOf("push"),
        sentAt = sentAt,
        isUnread = isUnread,
    )
}
