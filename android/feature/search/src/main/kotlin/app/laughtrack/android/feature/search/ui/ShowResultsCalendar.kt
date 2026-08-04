package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

internal const val SHOW_RESULTS_CALENDAR_TEST_TAG = "showResultsCalendar"

/**
 * Compact month grid for show discovery. Density is intentionally scoped to the
 * server's supported location/comedian/club dimensions; price and format facets
 * still apply to the result rows after a date is selected.
 */
@Composable
internal fun ShowResultsCalendar(
    selectedDateIso: String?,
    density: Map<String, Int>,
    densityLoading: Boolean,
    densityError: String?,
    onDisplayedMonthChange: (String) -> Unit,
    onSelectDate: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val today = LocalDate.now()
    val selectedDate = selectedDateIso?.let(::parseIsoDate) ?: today
    var displayedMonthIso by rememberSaveable { mutableStateOf(YearMonth.from(selectedDate).toString()) }
    val displayedMonth = runCatching { YearMonth.parse(displayedMonthIso) }.getOrDefault(YearMonth.from(today))

    LaunchedEffect(selectedDateIso) {
        selectedDateIso?.let(::parseIsoDate)?.let { externallySelected ->
            displayedMonthIso = YearMonth.from(externallySelected).toString()
        }
    }
    LaunchedEffect(displayedMonthIso) {
        onDisplayedMonthChange(displayedMonth.atDay(1).toString())
    }

    Surface(
        color = LaughTrackColors.Surface,
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
        modifier = modifier.fillMaxWidth().testTag(SHOW_RESULTS_CALENDAR_TEST_TAG),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Dots show dates with events for the selected location, comedian, or club.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            CalendarMonthHeader(
                month = displayedMonth,
                canGoBack = displayedMonth > YearMonth.from(today),
                onPrevious = { displayedMonthIso = displayedMonth.minusMonths(1).toString() },
                onNext = { displayedMonthIso = displayedMonth.plusMonths(1).toString() },
            )
            CalendarWeekdayHeader()
            monthCells(displayedMonth).chunked(7).forEach { week ->
                Row(modifier = Modifier.fillMaxWidth()) {
                    week.forEach { date ->
                        Box(modifier = Modifier.weight(1f), contentAlignment = Alignment.Center) {
                            if (date != null) {
                                CalendarDay(
                                    date = date,
                                    selected = date == selectedDate,
                                    today = date == today,
                                    enabled = !date.isBefore(today),
                                    showCount = density[date.toString()] ?: 0,
                                    onClick = { onSelectDate(date.toString()) },
                                )
                            }
                        }
                    }
                }
            }
            when {
                densityLoading ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    }
                densityError != null ->
                    Text(
                        "Show-date dots are temporarily unavailable.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
            }
        }
    }
}

@Composable
private fun CalendarMonthHeader(
    month: YearMonth,
    canGoBack: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onPrevious, enabled = canGoBack) {
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "Previous month")
        }
        Text(
            month.format(DateTimeFormatter.ofPattern("MMMM yyyy", Locale.US)),
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
        )
        IconButton(onClick = onNext) {
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "Next month")
        }
    }
}

@Composable
private fun CalendarWeekdayHeader() {
    val weekdays = listOf("S", "M", "T", "W", "T", "F", "S")
    Row(modifier = Modifier.fillMaxWidth()) {
        weekdays.forEach { label ->
            Text(
                label,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }
    }
}

@Composable
private fun CalendarDay(
    date: LocalDate,
    selected: Boolean,
    today: Boolean,
    enabled: Boolean,
    showCount: Int,
    onClick: () -> Unit,
) {
    val description =
        buildString {
            append(date.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.US))
            append(", ")
            append(date.format(DateTimeFormatter.ofPattern("MMMM d", Locale.US)))
            if (showCount > 0) append(", has shows")
            if (!enabled) append(", unavailable")
        }
    Column(
        modifier =
            Modifier
                .height(44.dp)
                .clip(RoundedCornerShape(10.dp))
                .clickable(enabled = enabled, onClick = onClick)
                .semantics { contentDescription = description },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Surface(
            shape = CircleShape,
            color = if (selected) LaughTrackColors.AccentStrong else Color.Transparent,
            border = if (today && !selected) BorderStroke(1.dp, LaughTrackColors.AccentStrong) else null,
            modifier = Modifier.size(30.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    date.dayOfMonth.toString(),
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                    color =
                        when {
                            selected -> LaughTrackColors.Foreground
                            enabled -> MaterialTheme.colorScheme.onSurface
                            else -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
                        },
                )
            }
        }
        Box(
            modifier =
                Modifier
                    .padding(top = 2.dp)
                    .size(4.dp)
                    .clip(CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            if (showCount > 0) {
                Surface(color = LaughTrackColors.AccentStrong, shape = CircleShape, modifier = Modifier.size(4.dp)) {}
            }
        }
    }
}

internal fun monthCells(month: YearMonth): List<LocalDate?> {
    val leadingEmptyDays = month.atDay(1).dayOfWeek.value % 7
    val cells = MutableList<LocalDate?>(leadingEmptyDays) { null }
    cells += (1..month.lengthOfMonth()).map(month::atDay)
    while (cells.size % 7 != 0) cells += null
    return cells
}

private fun parseIsoDate(value: String): LocalDate? = runCatching { LocalDate.parse(value) }.getOrNull()
