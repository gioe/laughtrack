package app.laughtrack.android.feature.notifications

import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.NotificationComedian
import app.laughtrack.android.core.network.generated.model.NotificationItem
import app.laughtrack.android.core.network.generated.model.NotificationShow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZonedDateTime

class NotificationCenterPresentationTest {
    private val now = ZonedDateTime.parse("2026-07-15T15:00:00-04:00")

    @Test
    fun compactNotificationCenterPreservesPhoneComposition() {
        listOf(440.dp, 599.dp).forEach { width ->
            val spec = notificationCenterLayoutSpec(width)

            assertEquals(NotificationCenterLayoutMode.Compact, spec.mode)
            assertEquals(720.dp, spec.contentMaxWidth)
            assertEquals(16.dp, spec.horizontalPadding)
            assertFalse(spec.centerSparseContent)
        }
    }

    @Test
    fun shippingTabletsUseBoundedCenteredNotificationCompositions() {
        val sevenInch = notificationCenterLayoutSpec(600.dp)
        val tenInch = notificationCenterLayoutSpec(800.dp)
        val veryWide = notificationCenterLayoutSpec(1_600.dp)

        assertEquals(NotificationCenterLayoutMode.Expanded, sevenInch.mode)
        assertEquals(560.dp, sevenInch.contentMaxWidth)
        assertTrue(sevenInch.centerSparseContent)
        assertEquals(NotificationCenterLayoutMode.Expanded, tenInch.mode)
        assertEquals(720.dp, tenInch.contentMaxWidth)
        assertTrue(tenInch.centerSparseContent)
        assertEquals(720.dp, veryWide.contentMaxWidth)
    }

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

    @Test
    fun recentIsTheNewestFirstDefaultWithDeterministicEqualTimestampOrdering() {
        val items =
            listOf(
                item(title = "oldest", sentAt = "2026-07-13T15:00:00-04:00"),
                item(title = "equal-b", sentAt = "2026-07-15T13:00:00-04:00"),
                item(title = "equal-a", sentAt = "2026-07-15T13:00:00-04:00"),
            )

        assertEquals(NotificationSortOrder.RECENT, DEFAULT_NOTIFICATION_SORT_ORDER)
        assertEquals(
            listOf("equal-a", "equal-b", "oldest"),
            DEFAULT_NOTIFICATION_SORT_ORDER.sorted(items).map { it.id },
        )
    }

    @Test
    fun oldestSelectionOrdersOldestFirstWithTheSameDeterministicTiebreaker() {
        val items =
            listOf(
                item(title = "equal-b", sentAt = "2026-07-15T13:00:00-04:00"),
                item(title = "oldest", sentAt = "2026-07-13T15:00:00-04:00"),
                item(title = "equal-a", sentAt = "2026-07-15T13:00:00-04:00"),
            )

        assertEquals(
            listOf("oldest", "equal-a", "equal-b"),
            NotificationSortOrder.OLDEST.sorted(items).map { it.id },
        )
    }

    @Test
    fun sortingPreservesUnreadPresentationAndComedianNavigationActions() {
        val unreadShow =
            item(
                title = "unread-show",
                isUnread = true,
                sentAt = "2026-07-15T13:00:00-04:00",
                comedianNames = listOf("Taylor Tomlinson"),
            ).let { item ->
                item.copy(
                    shows = notificationShows(101),
                    comedians = item.comedians.map { it.copy(showIds = listOf(101)) },
                )
            }
        val grouped =
            item(
                title = "grouped",
                isUnread = false,
                sentAt = "2026-07-14T13:00:00-04:00",
                comedianNames = listOf("Taylor Tomlinson", "Sam Jay"),
            ).let { item ->
                item.copy(
                    shows = notificationShows(201, 202),
                    comedians =
                        item.comedians.mapIndexed { index, comedian ->
                            comedian.copy(showIds = listOf(201 + index))
                        },
                    route = "favorites",
                )
            }
        val sorted = NotificationSortOrder.OLDEST.sorted(listOf(unreadShow, grouped))

        assertEquals(listOf("grouped", "unread-show"), sorted.map { it.id })
        assertTrue(notificationRowPresentation(sorted.last(), now).isUnread)
        assertFalse(notificationRowPresentation(sorted.first(), now).isUnread)
        val firstComedian = unreadShow.comedians.single()
        val groupedComedians = grouped.comedians
        assertEquals(AppRoute.ComedianDetail(100, listOf(101)), firstComedian.detailRoute())
        assertEquals(
            listOf(
                AppRoute.ComedianDetail(100, listOf(201)),
                AppRoute.ComedianDetail(101, listOf(202)),
            ),
            groupedComedians.map { it.detailRoute() },
        )
    }

    private fun item(
        title: String,
        body: String = "",
        isUnread: Boolean = false,
        sentAt: String = "2026-07-15T13:00:00-04:00",
        comedianNames: List<String> = emptyList(),
    ) = NotificationItem(
        id = title,
        title = title,
        body = body,
        comedianName = comedianNames.firstOrNull().orEmpty(),
        comedianImageUrl = "",
        comedians =
            comedianNames.mapIndexed { index, name ->
                NotificationComedian(
                    id = 100 + index,
                    comedianId = "comedian-$index",
                    comedianName = name,
                    comedianImageUrl = "",
                    showIds = emptyList(),
                )
            },
        shows = emptyList(),
        channels = listOf("push"),
        sentAt = sentAt,
        isUnread = isUnread,
    )

    private fun notificationShows(vararg showIds: Int) =
        showIds.map { showId ->
            NotificationShow(
                showId = showId,
                subtitle = "Show $showId",
            )
        }
}
