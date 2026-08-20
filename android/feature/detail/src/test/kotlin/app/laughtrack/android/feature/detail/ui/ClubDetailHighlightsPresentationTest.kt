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
    fun marquee_deduplicates_and_ranks_unique_evening_performers() {
        val canonical = lineup(1, "First", 100, 1)
        val summary =
            clubMarqueeSummary(
                highlights(
                    tonight =
                        listOf(
                            show(
                                1,
                                lineup =
                                    listOf(
                                        canonical,
                                        lineup(2, "Second", 90, 10),
                                        lineup(4, "Fourth", 90, 5),
                                    ),
                            ),
                            show(
                                2,
                                lineup =
                                    listOf(
                                        lineup(99, "Alias", 1, 1, parent = canonical),
                                        lineup(3, "Third", 90, 10),
                                        lineup(5, "Fifth", 80, 50),
                                    ),
                            ),
                        ),
                ),
            )!!

        assertEquals(listOf("First", "Second", "Third"), summary.performers.map { it.name })
    }

    @Test
    fun marquee_uses_show_count_then_id_as_deterministic_ranking_fallbacks() {
        val summary =
            clubMarqueeSummary(
                highlights(
                    tonight =
                        listOf(
                            show(
                                1,
                                lineup =
                                    listOf(
                                        lineup(30, "Higher ID", 50, 5),
                                        lineup(20, "Lower ID", 50, 5),
                                        lineup(10, "Higher count", 50, 10),
                                        lineup(40, "Excluded", 50, 1),
                                    ),
                            ),
                        ),
                ),
            )!!

        assertEquals(listOf("Higher count", "Lower ID", "Higher ID"), summary.performers.map { it.name })
    }

    @Test
    fun marquee_pairs_each_ranked_performer_with_their_earliest_show_time() {
        val canonical = lineup(1, "Canonical headliner", 100, 5)
        val later =
            show(
                id = 1,
                date = "2026-07-30T22:00:00-04:00",
                timezone = "America/Los_Angeles",
                lineup =
                    listOf(
                        canonical,
                        lineup(3, "Late set", 80, 5),
                    ),
            )
        val earlier =
            show(
                id = 2,
                date = "2026-07-30T20:00:00-04:00",
                timezone = "America/New_York",
                lineup =
                    listOf(
                        lineup(99, "Alias", 1, 1, parent = canonical),
                        lineup(2, "Early set", 90, 5),
                    ),
            )
        val summary = clubMarqueeSummary(highlights(tonight = listOf(later, earlier)))!!

        assertEquals(
            listOf(
                ClubMarqueePerformer("Canonical headliner", localizedTime(earlier)),
                ClubMarqueePerformer("Early set", localizedTime(earlier)),
                ClubMarqueePerformer("Late set", localizedTime(later)),
            ),
            summary.performers,
        )
    }

    @Test
    fun marquee_handles_single_performer_and_missing_lineup_title_fallbacks() {
        val single =
            clubMarqueeSummary(
                highlights(tonight = listOf(show(1, lineup = listOf(lineup(1, "Solo", 5, 1))))),
            )!!
        assertEquals(
            listOf(ClubMarqueePerformer("Solo", localizedTime(show(1)))),
            single.performers,
        )

        val missing =
            clubMarqueeSummary(
                highlights(
                    tonight =
                        listOf(
                            show(2, name = "Later", date = "2026-07-30T22:00:00-04:00", lineup = null),
                            show(1, name = "Early", date = "2026-07-30T20:00:00-04:00", lineup = emptyList()),
                        ),
                ),
            )!!
        assertEquals(
            listOf(ClubMarqueePerformer("Early", localizedTime(show(1)))),
            missing.performers,
        )
        assertEquals(
            listOf(ClubMarqueePerformer("Show", localizedTime(show(3)))),
            clubMarqueeSummary(highlights(tonight = listOf(show(3, name = " "))))!!.performers,
        )
    }

    @Test
    fun next_up_is_used_only_when_the_tonight_marquee_is_empty() {
        val next = show(2)

        assertNull(clubNextFeaturedShow(highlights(tonight = listOf(show(1)), next = next)))
        val featured = clubNextFeaturedShow(highlights(next = next))
        assertEquals("Next up", featured?.eyebrow)
        assertEquals(2, featured?.show?.id)
        assertNull(clubNextFeaturedShow(highlights()))
        assertNull(clubMarqueeSummary(highlights(next = next)))
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
    fun source_renders_three_performer_time_rows_without_a_summary_footer() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("summary.performers.forEachIndexed"))
        assertTrue(source.contains("performer.localizedStartTime.uppercase"))
        assertFalse(source.contains("remainingPerformerCount"))
        assertFalse(source.contains("localizedStartTimes.joinToString"))
        assertFalse(source.contains("View all"))
        assertFalse(source.contains("AppRoute.ShowDetail(row.show.id)"))
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
    fun source_preserves_the_independent_calendar_filter_without_a_marquee_action() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("mutableStateOf(ClubCalendarFilter.AnyDate)"))
        assertTrue(source.contains("onFilter = { calendarFilter = it }"))
        assertTrue(source.contains("if (filter == ClubCalendarFilter.Today)"))
        assertTrue(source.contains("testTag(CLUB_CALENDAR_SECTION_TEST_TAG)"))
        assertFalse(source.contains("onShowAll"))
        assertFalse(source.contains("BringIntoViewRequester"))
        assertFalse(source.contains("CLUB_HIGHLIGHT_SHOW_ALL_TEST_TAG"))
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

    @Test
    fun venue_artwork_renders_before_the_tonight_marquee_with_image_fallback() {
        val source = clubDetailScreenSource()
        val posterCall = "ClubPoster(url = club.heroImageUrl.ifBlank { club.imageUrl }, contentDescription = club.name)"
        val titlePosition = source.indexOf("club.name.uppercase()")
        val actionsPosition = source.indexOf("ClubHeroAction(label = \"Website\"")
        val posterPosition = source.indexOf(posterCall, actionsPosition)
        val boardPosition = source.indexOf("ClubTonightMarqueeSection(", actionsPosition)

        assertTrue(titlePosition >= 0)
        assertTrue(actionsPosition > titlePosition)
        assertTrue(posterPosition > actionsPosition)
        assertTrue(boardPosition > posterPosition)
        assertTrue(source.lineSequence().any { it.trim() == posterCall })
        assertFalse(source.lineSequence().any { it.trim() == "// $posterCall" })
        assertTrue(source.contains("verticalArrangement = Arrangement.spacedBy(10.dp)"))
        assertTrue(source.contains(".size(206.dp)"))
        assertTrue(source.contains("fallback = RemoteImageFallback.Club"))
        assertTrue(source.contains("\"TONIGHT\""))
        assertTrue(source.contains("ClubMarqueePaper"))
        assertTrue(source.contains("ClubMarqueeInk.copy(alpha = 0.72f)"))
        assertTrue(source.contains("ClubBulb.copy(alpha = 0.42f)"))
    }

    @Test
    fun venue_action_pills_preserve_external_destinations_and_accessibility() {
        val source = clubDetailScreenSource()

        assertTrue(source.contains("ClubHeroAction(label = \"Website\""))
        assertTrue(source.contains("ClubHeroAction(label = \"Directions\""))
        assertTrue(source.contains("context.openUrl(club.website)"))
        assertTrue(source.contains("context.openMap(club.address)"))
        assertTrue(source.contains("semantics { contentDescription = label }"))
        assertTrue(source.contains("clickable(role = Role.Button, onClick = onClick)"))
        assertTrue(source.contains("heightIn(min = 48.dp)"))
        assertTrue(source.contains("color = ClubMarqueeInk.copy(alpha = 0.82f)"))
        assertTrue(source.contains("contentColor = ClubMarqueePaper"))
        assertTrue(source.contains("AppRoute.ShowDetail(featured.show.id)"))
        assertTrue(source.contains("club.heroImageUrl.ifBlank { club.imageUrl }"))
        assertTrue(source.contains("fallback = RemoteImageFallback.Club"))
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
        parent: ComedianLineup? = null,
    ) = ComedianLineup(
        id = id,
        uuid = "lineup-$id",
        name = name,
        imageUrl = "https://example.com/comedian-$id.jpg",
        socialData = SocialData(id = id, popularity = BigDecimal.valueOf(popularity.toLong())),
        showCount = showCount,
        parentComedian = parent,
    )

    private fun localizedTime(show: Show): String =
        parseShowDateTime(show.date, show.timezone)!!
            .toLocalTime()
            .format(
                DateTimeFormatter
                    .ofLocalizedTime(FormatStyle.SHORT)
                    .withLocale(Locale.getDefault()),
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
