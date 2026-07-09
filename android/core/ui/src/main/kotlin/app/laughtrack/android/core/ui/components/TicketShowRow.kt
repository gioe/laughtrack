package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.laughtrack.android.core.ui.theme.LaughTrackColors

/**
 * Color slots for [TicketShowRow]: the paper body, the hairline border, the dashed
 * perforation, and the date stub. Defaults to the cream ticket palette via
 * [TicketShowRowDefaults.creamColors].
 */
data class TicketShowRowColors(
    val paper: Color,
    val border: Color,
    val divider: Color,
    val stub: TicketStubColors,
)

object TicketShowRowDefaults {
    /** The shared cream ticket palette (LaughTrackColors.Ticket* tokens). */
    val creamColors =
        TicketShowRowColors(
            paper = LaughTrackColors.TicketPaper,
            border = LaughTrackColors.TicketBorder,
            divider = LaughTrackColors.TicketBorder,
            stub =
                TicketStubColors(
                    background = LaughTrackColors.TicketStub,
                    accent = LaughTrackColors.TicketAccent,
                    primary = LaughTrackColors.TicketInk,
                    muted = LaughTrackColors.TicketInkMuted,
                ),
        )

    /** Row min height used by the search and home show lists. */
    val MinHeight = 104.dp

    /** Row min height used by the compact detail-screen show lists. */
    val CompactMinHeight = 88.dp
}

/**
 * The shared "ticket" show row shell mirroring the iOS ShowRow ticket presentation:
 * a bordered paper Surface sized to its tallest segment, a caller-supplied [body],
 * a dashed perforation, and a fixed-width date/price [TicketStub]. Home, search,
 * and the detail screens all render their show rows through this one assembly so
 * styling tweaks (min height, padding, corner radius) happen in one place.
 *
 * [body] receives the modifier that fills the flexible left segment; apply content
 * padding and alignment inside the slot.
 */
@Composable
fun TicketShowRow(
    dateParts: TicketDateParts,
    priceLabel: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    colors: TicketShowRowColors = TicketShowRowDefaults.creamColors,
    minHeight: Dp = TicketShowRowDefaults.MinHeight,
    body: @Composable (Modifier) -> Unit,
) {
    Surface(
        modifier =
            modifier
                .fillMaxWidth()
                .height(IntrinsicSize.Min)
                .clip(RoundedCornerShape(12.dp))
                .clickable(onClick = onClick)
                .border(1.dp, colors.border, RoundedCornerShape(12.dp)),
        color = colors.paper,
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .heightIn(min = minHeight),
        ) {
            body(
                Modifier
                    .weight(1f)
                    .fillMaxHeight(),
            )
            TicketDashedDivider(
                color = colors.divider,
                modifier =
                    Modifier
                        .fillMaxHeight()
                        .padding(vertical = 10.dp),
            )
            TicketStub(
                dateParts = dateParts,
                priceLabel = priceLabel,
                colors = colors.stub,
                modifier =
                    Modifier
                        .width(88.dp)
                        .fillMaxHeight(),
            )
        }
    }
}

/**
 * Cream ticket row with the standard compact body — artwork thumbnail plus
 * title/subtitle in ticket ink — mirroring the iOS ShowRow `.compactTicket`
 * presentation. Used by the Comedian-detail upcoming/past show lists and the
 * Show-detail "More shows" list. Non-show lists (e.g. podcast appearances) keep
 * their plain rows — they are not ticketed events.
 */
@Composable
fun TicketShowRow(
    title: String,
    subtitle: String?,
    imageUrl: String?,
    dateParts: TicketDateParts,
    priceLabel: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    TicketShowRow(
        dateParts = dateParts,
        priceLabel = priceLabel,
        onClick = onClick,
        modifier = modifier,
        minHeight = TicketShowRowDefaults.CompactMinHeight,
    ) { bodyModifier ->
        Row(
            modifier = bodyModifier.padding(10.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RemoteImage(
                url = imageUrl,
                contentDescription = title,
                modifier = Modifier.size(56.dp).clip(RoundedCornerShape(8.dp)),
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleSmall,
                    color = LaughTrackColors.TicketInk,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                subtitle?.takeIf { it.isNotBlank() }?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = LaughTrackColors.TicketInkMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}
