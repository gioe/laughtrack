package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class TicketDateParts(
    val weekday: String,
    val day: String,
    val month: String,
    val time: String,
)

data class TicketStubColors(
    val background: Color,
    val accent: Color,
    val primary: Color,
    val muted: Color,
)

private val TicketWeekdayFormatter = DateTimeFormatter.ofPattern("EEE", Locale.US)
private val TicketDayFormatter = DateTimeFormatter.ofPattern("d", Locale.US)
private val TicketMonthFormatter = DateTimeFormatter.ofPattern("MMM", Locale.US)
private val TicketTimeFormatter = DateTimeFormatter.ofPattern("h:mm a", Locale.US)

fun ticketStubDateParts(
    isoDateTime: String?,
    timezone: String?,
    fallbackTime: String = "",
): TicketDateParts =
    runCatching {
        val zone = timezone?.let(ZoneId::of) ?: ZoneId.systemDefault()
        val dateTime = OffsetDateTime.parse(isoDateTime).atZoneSameInstant(zone)
        TicketDateParts(
            weekday = dateTime.format(TicketWeekdayFormatter).uppercase(Locale.US),
            day = dateTime.format(TicketDayFormatter),
            month = dateTime.format(TicketMonthFormatter).uppercase(Locale.US),
            time = dateTime.format(TicketTimeFormatter),
        )
    }.getOrElse {
        TicketDateParts(weekday = "", day = "", month = "", time = fallbackTime)
    }

@Composable
fun TicketDashedDivider(
    color: Color,
    modifier: Modifier = Modifier,
) {
    Canvas(modifier = modifier.width(1.dp)) {
        drawLine(
            color = color,
            start = Offset(size.width / 2, 0f),
            end = Offset(size.width / 2, size.height),
            strokeWidth = 1.dp.toPx(),
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f)),
        )
    }
}

@Composable
fun TicketStub(
    dateParts: TicketDateParts,
    priceLabel: String?,
    colors: TicketStubColors,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier =
            modifier
                .background(colors.background)
                .padding(vertical = 10.dp, horizontal = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            dateParts.weekday,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.4.sp),
            color = colors.accent,
            maxLines = 1,
        )
        Text(
            dateParts.day,
            fontWeight = FontWeight.Black,
            fontSize = 26.sp,
            color = colors.primary,
            maxLines = 1,
        )
        Text(
            dateParts.month,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 1.2.sp),
            color = colors.muted,
            maxLines = 1,
        )
        Text(
            dateParts.time,
            style = MaterialTheme.typography.labelSmall,
            color = colors.muted,
            maxLines = 1,
            modifier = Modifier.padding(top = 2.dp),
        )
        if (priceLabel != null) {
            Text(
                priceLabel,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = colors.accent,
                maxLines = 1,
                modifier = Modifier.padding(top = 2.dp),
            )
        }
    }
}
