package app.laughtrack.android.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.util.Locale

data class TonightHeroCardContent(
    val timeLabel: String,
    val title: String,
    val venueLabel: String,
    val artworkUrl: String?,
    val artworkCaption: String,
    val artworkContentDescription: String,
    val artworkFallback: RemoteImageFallback,
    val priceLabel: String?,
)

/**
 * Shared show-hero presentation used by Discover's Tonight carousel and compact
 * destination highlights. Callers own section chrome and accessibility tags.
 */
@Composable
fun TonightHeroCard(
    content: TonightHeroCardContent,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    artworkHeight: Dp = 198.dp,
) {
    Column(
        modifier = modifier.clickable(role = Role.Button, onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TonightHeroArtwork(content = content, height = artworkHeight)
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth().weight(1f),
        ) {
            Text(
                text = content.timeLabel,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Black,
                fontSize = 30.sp,
                maxLines = 1,
            )
            Text(
                text = content.title.uppercase(Locale.US),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Black),
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = content.venueLabel.uppercase(Locale.US),
                style =
                    MaterialTheme.typography.labelSmall.copy(
                        fontSize = 9.sp,
                        fontWeight = FontWeight.SemiBold,
                        letterSpacing = 2.sp,
                    ),
                textAlign = TextAlign.Center,
                color = LaughTrackColors.AccentStrong,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.weight(1f))
            TonightPricePill(content.priceLabel)
        }
    }
}

@Composable
private fun TonightHeroArtwork(
    content: TonightHeroCardContent,
    height: Dp,
) {
    val posterHeight = (height - 28.dp).coerceAtLeast(108.dp)
    val imageHeight = (posterHeight - 38.dp).coerceAtLeast(76.dp)
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(height)
                .clip(RoundedCornerShape(16.dp))
                .background(
                    Brush.radialGradient(
                        listOf(
                            LaughTrackColors.AccentStrong.copy(alpha = 0.24f),
                            LaughTrackColors.Surface.copy(alpha = 0.96f),
                        ),
                    ),
                ),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier =
                Modifier
                    .width(154.dp)
                    .height(posterHeight)
                    .clip(RoundedCornerShape(8.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(
                                LaughTrackColors.Foreground.copy(alpha = 0.94f),
                                Color(0xFFD1C2A8),
                            ),
                        ),
                    )
                    .border(2.dp, Color.Black.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
                    .padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(5.dp),
        ) {
            RemoteImage(
                url = content.artworkUrl,
                fallback = content.artworkFallback,
                contentDescription = content.artworkContentDescription,
                modifier =
                    Modifier
                        .width(138.dp)
                        .height(imageHeight)
                        .clip(RectangleShape)
                        .border(1.dp, Color.Black.copy(alpha = 0.5f), RectangleShape),
            )
            Text(
                text = content.artworkCaption.uppercase(Locale.US),
                style =
                    MaterialTheme.typography.labelSmall.copy(
                        fontFamily = FontFamily.Serif,
                        fontWeight = FontWeight.SemiBold,
                    ),
                color = Color.Black.copy(alpha = 0.74f),
                textAlign = TextAlign.Center,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().background(Color.White.copy(alpha = 0.30f)),
            )
        }
    }
}

@Composable
private fun TonightPricePill(price: String?) {
    Box(
        modifier = Modifier.fillMaxWidth().height(38.dp),
        contentAlignment = Alignment.Center,
    ) {
        if (price != null) {
            Surface(
                color = LaughTrackColors.AccentStrong,
                shape = RoundedCornerShape(999.dp),
            ) {
                Text(
                    text = price,
                    color = MaterialTheme.colorScheme.onSurface,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Black),
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                )
            }
        }
    }
}
