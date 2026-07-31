package app.laughtrack.android.feature.detail.ui

import app.laughtrack.android.core.network.generated.model.ClubHighlights
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.ComedianListItem
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.feature.detail.util.parseShowDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

class ClubDetailHighlightsPresentationTest {
    @Test
    fun marquee_selects_three_most_popular_shows_then_displays_them_chronologically() {
        val rows =
            clubMarqueeRows(
                highlights(
                    tonight =
                        listOf(
                            show(1, date = "2026-07-30T22:00:00-04:00", lineup = listOf(lineup(1, "Third", 100, 2))),
                            show(2, date = "2026-07-30T20:00:00-04:00", lineup = listOf(lineup(2, "First", 80, 2))),
                            show(3, date = "2026-07-30T21:00:00-04:00", lineup = listOf(lineup(3, "Second", 90, 2))),
                            show(4, date = "2026-07-30T19:00:00-04:00", lineup = listOf(lineup(4, "Excluded", 10, 50))),
                        ),
                ),
            )

        assertEquals(listOf(2, 3, 1), rows.map { it.show.id })
        assertEquals(listOf("First", "Second", "Third"), rows.map { it.performerName })
    }

    @Test
    fun marquee_uses_show_count_then_date_and_id_as_deterministic_fallbacks() {
        val rows =
            clubMarqueeRows(
                highlights(
                    tonight =
                        listOf(
                            show(30, lineup = listOf(lineup(30, "Higher ID", 50, 5))),
                            show(20, lineup = listOf(lineup(20, "Lower ID", 50, 5))),
                            show(10, lineup = listOf(lineup(10, "Higher count", 50, 10))),
                            show(40, lineup = listOf(lineup(40, "Excluded", 50, 1))),
                        ),
                ),
            )

        assertEquals(listOf(10, 20, 30), rows.map { it.show.id })

        val noLineup =
            clubMarqueeRows(
                highlights(tonight = listOf(show(50, name = "No lineup", lineup = null))),
            )
        assertEquals("No lineup", noLineup.single().performerName)
    }

    @Test
    fun marquee_uses_each_venue_timezone_and_the_current_locale_for_start_times() {
        val show =
            show(
                id = 1,
                date = "2026-07-31T00:00:00Z",
                timezone = "America/Los_Angeles",
                lineup = listOf(lineup(1, "Local headliner", 100, 5)),
            )
        val row = clubMarqueeRows(highlights(tonight = listOf(show))).single()
        val expected =
            parseShowDateTime(show.date, show.timezone)!!
                .toLocalTime()
                .format(
                    DateTimeFormatter
                        .ofLocalizedTime(FormatStyle.SHORT)
                        .withLocale(Locale.getDefault()),
                )

        assertEquals(expected, row.localizedStartTime)
    }

    @Test
    fun next_up_is_used_only_when_the_tonight_marquee_is_empty() {
        val next = show(2)

        assertNull(clubNextFeaturedShow(highlights(tonight = listOf(show(1)), next = next)))
        val featured = clubNextFeaturedShow(highlights(next = next))
        assertEquals("Next up", featured?.eyebrow)
        assertEquals(2, featured?.show?.id)
        assertNull(clubNextFeaturedShow(highlights()))
        assertTrue(clubMarqueeRows(highlights(next = next)).isEmpty())
    }

    @Test
    fun today_filter_compares_dates_in_each_show_venue_timezone() {
        val now = Instant.parse("2026-07-31T03:30:00Z")
        val losAngelesToday =
            show(1, date = "2026-07-31T02:00:00Z", timezone = "America/Los_Angeles")
        val losAngelesTomorrow =
            show(2, date = "2026-07-31T08:00:00Z", timezone = "America/Los_Angeles")
        val newYorkToday =
            show(3, date = "2026-07-30T23:00:00-04:00", timezone = "America/New_York")
        val shows = listOf(losAngelesToday, losAngelesTomorrow, newYorkToday)

        assertEquals(shows, clubCalendarShows(shows, ClubCalendarFilter.AnyDate, now))
        assertEquals(
            listOf(losAngelesToday, newYorkToday),
            clubCalendarShows(shows, ClubCalendarFilter.Today, now),
        )
    }

    @Test
    fun frequent_performers_are_exposed_only_when_present() {
        assertTrue(clubFrequentPerformers(highlights()).isEmpty())

        val performer = performer(8, "Aparna Nancherla")
        assertEquals(listOf(performer), clubFrequentPerformers(highlights(performers = listOf(performer))))
    }

    @Test
    fun source_wires_each_marquee_row_to_its_show_detail() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("AppRoute.ShowDetail(row.show.id)"))
        assertTrue(source.contains("testTag(\"\$CLUB_HIGHLIGHT_SHOW_TEST_TAG_PREFIX\${row.show.id}\")"))
        assertTrue(source.contains("clickable(role = Role.Button)"))
        assertTrue(source.contains("AppRoute.ComedianDetail(it.id)"))
    }

    @Test
    fun source_renders_the_optional_home_action_without_changing_back_or_favorite_actions() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("onHome: (() -> Unit)? = null"))
        assertTrue(source.contains("onHome?.let"))
        assertTrue(source.contains("ClubChromeButton(onClick = it)"))
        assertTrue(source.contains("Icons.Filled.Home, contentDescription = \"Home\""))
        assertTrue(source.contains("ClubChromeButton(onClick = onBack)"))
        assertTrue(source.contains("Icons.AutoMirrored.Filled.ArrowBack, contentDescription = \"Back\""))
        assertTrue(source.contains("ClubChromeButton(onClick = onFavorite, enabled = !isFavoritePending)"))
    }

    @Test
    fun frequent_performers_render_after_the_calendar_and_related_venues() {
        val source = clubDetailScreenSource()
        val calendarPosition = source.indexOf("ClubCalendarSection(")
        val relatedVenuesPosition = source.indexOf("ClubRelatedVenuesSection(")
        val frequentPerformersPosition = source.indexOf("ClubFrequentPerformersSection(")

        assertTrue(calendarPosition >= 0)
        assertTrue(relatedVenuesPosition > calendarPosition)
        assertTrue(frequentPerformersPosition > relatedVenuesPosition)
    }

    @Test
    fun source_wires_show_all_to_today_and_the_calendar_without_disabling_controls() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("calendarFilter = ClubCalendarFilter.Today"))
        assertTrue(source.contains("calendarBringIntoViewRequester.bringIntoView()"))
        assertTrue(source.contains("bringIntoViewRequester(calendarBringIntoViewRequester)"))
        assertTrue(source.contains("onFilter = { calendarFilter = it }"))
        assertTrue(source.contains("\"Show all\""))
        assertTrue(source.contains("testTag(CLUB_CALENDAR_SECTION_TEST_TAG)"))
    }

    @Test
    fun source_uses_the_white_and_black_bulb_marquee_without_a_tonight_heading() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("ClubMarqueePaper"))
        assertTrue(source.contains("color = Color.Black"))
        assertTrue(source.contains("ClubBulb"))
        assertTrue(source.contains("Canvas"))
        assertFalse(source.contains("ClubFeaturedShow(\"Tonight\""))
        assertFalse(source.contains("\"Tonight's marquee\""))
    }

    private fun highlights(
        tonight: List<Show> = emptyList(),
        next: Show? = null,
        performers: List<ComedianListItem> = emptyList(),
    ) = ClubHighlights(
        tonightShows = tonight,
        nextShow = next,
        frequentPerformers = performers,
    )

    private fun show(
        id: Int,
        name: String = "Show $id",
        date: String = "2026-07-30T20:00:00-04:00",
        timezone: String? = "America/New_York",
        lineup: List<ComedianLineup>? = null,
    ) = Show(
        id = id,
        clubId = 42,
        date = date,
        imageUrl = "https://example.com/show-$id.jpg",
        name = name,
        timezone = timezone,
        lineup = lineup,
    )

    private fun lineup(
        id: Int,
        name: String,
        popularity: Int,
        showCount: Int?,
    ) = ComedianLineup(
        id = id,
        uuid = "lineup-$id",
        name = name,
        imageUrl = "https://example.com/comedian-$id.jpg",
        socialData = SocialData(id = id, popularity = BigDecimal.valueOf(popularity.toLong())),
        showCount = showCount,
    )

    private fun performer(
        id: Int,
        name: String,
    ) = ComedianListItem(
        id = id,
        uuid = "uuid-$id",
        name = name,
        imageUrl = "https://example.com/comedian-$id.jpg",
        socialData = SocialData(id),
        showCount = 12,
    )

    private fun clubDetailScreenSource(): String = String(Files.readAllBytes(clubDetailScreenPath()))

    private fun clubDetailScreenPath(): Path {
        val relativePaths =
            listOf(
                Paths.get(
                    "android/feature/detail/src/main/kotlin",
                    "app/laughtrack/android/feature/detail/ui/ClubDetailScreen.kt",
                ),
                Paths.get(
                    "feature/detail/src/main/kotlin/app/laughtrack/android/feature/detail/ui/ClubDetailScreen.kt",
                ),
            )
        return generateSequence(Paths.get("").toAbsolutePath()) { it.parent }
            .flatMap { directory -> relativePaths.asSequence().map(directory::resolve) }
            .firstOrNull(Files::isRegularFile)
            ?: error("Unable to locate ClubDetailScreen.kt from ${Paths.get("").toAbsolutePath()}")
    }
}
