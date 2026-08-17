package app.laughtrack.android.feature.search.ui

import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.feature.search.model.SearchResult
import app.laughtrack.android.feature.search.model.ShowDateShortcut
import app.laughtrack.android.feature.search.model.ShowFormatOption
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.time.LocalDate
import java.time.YearMonth

class ShowSearchPresentationTest {
    @Test
    fun `show controls keep format facets in the additional filters sheet`() {
        val source = readMainSource("ui/SearchScreen.kt")
        val showBlock =
            source
                .substringAfter("private fun ShowSearchControls(")
                .substringBefore("private fun ShowFacetChip(")

        val intro = showBlock.indexOf("Start with what matters")
        val shortcuts = showBlock.indexOf("ShowDateShortcut.entries")
        val location = showBlock.indexOf("LocationPill")
        val additionalFilters = showBlock.indexOf("label = \"More filters\"")
        val optional = showBlock.indexOf("Add comedian or club")
        val comedianField = showBlock.indexOf("Comedian (optional)")

        assertTrue(intro >= 0)
        assertTrue(shortcuts > intro)
        assertTrue(location > shortcuts)
        assertTrue(additionalFilters > location)
        assertFalse(showBlock.contains("label = \"Free\""))
        assertFalse(showBlock.contains("label = ShowFormatOption.OPEN_MIC.label"))
        assertFalse(showBlock.contains("ShowFormatOption.entries.filterNot"))
        assertTrue(showBlock.contains("filters.filterNot { it.slug in legacyPriceSlugs }"))
        assertTrue(optional > shortcuts)
        assertTrue(comedianField > optional)
        assertFalse(showBlock.contains("value = query.text"))
        assertTrue(showBlock.contains("ShowMaximumPriceOption"))
        assertEquals(listOf("Tonight", "This Weekend"), ShowDateShortcut.entries.map { it.label })
        assertEquals("Open mic", ShowFormatOption.OPEN_MIC.label)
    }

    @Test
    fun `calendar presentation is wired to density and exact date selection`() {
        val screen = readMainSource("ui/SearchScreen.kt")
        val calendar = readMainSource("ui/ShowResultsCalendar.kt")

        assertTrue(screen.contains("ShowResultsPresentation.CALENDAR"))
        assertTrue(screen.contains("density = pivotState.showDensity"))
        assertTrue(screen.contains("onSelectDate = viewModel::selectShowCalendarDate"))
        assertTrue(calendar.contains("broad guide to dates with shows"))
        assertTrue(calendar.contains("Price and format filters apply after you pick a day"))
    }

    @Test
    fun `agenda groups and sorts shows by venue local day`() {
        val latePacific = show(1, "2026-08-05T02:30:00Z", "America/Los_Angeles")
        val earlyPacific = show(2, "2026-08-04T18:00:00-07:00", "America/Los_Angeles")
        val nextDay = show(3, "2026-08-05T20:00:00-07:00", "America/Los_Angeles")

        val sections = showAgendaSections(listOf(nextDay, latePacific, earlyPacific))

        assertEquals(listOf("2026-08-04", "2026-08-05"), sections.map { it.key })
        assertEquals(listOf(2, 1), sections.first().shows.map { (it.route as AppRoute.ShowDetail).id })
        assertEquals(listOf(3), sections.last().shows.map { (it.route as AppRoute.ShowDetail).id })
    }

    @Test
    fun `month grid starts on Sunday columns and contains complete weeks`() {
        val cells = monthCells(YearMonth.of(2026, 8))

        assertEquals(7, cells.take(7).size)
        assertEquals(6, cells.indexOf(LocalDate.of(2026, 8, 1)))
        assertEquals(0, cells.size % 7)
        assertEquals(LocalDate.of(2026, 8, 31), cells.filterNotNull().last())
    }

    private fun show(
        id: Int,
        date: String,
        timezone: String,
    ) = SearchResult(
        title = "Show $id",
        subtitle = "Comedy Room",
        imageUrl = null,
        route = AppRoute.ShowDetail(id),
        showDate = date,
        showTimezone = timezone,
    )

    private fun readMainSource(relative: String): String {
        val candidates =
            listOf(
                File("feature/search/src/main/kotlin/app/laughtrack/android/feature/search/$relative"),
                File("src/main/kotlin/app/laughtrack/android/feature/search/$relative"),
            )
        return candidates.first(File::exists).readText()
    }
}
