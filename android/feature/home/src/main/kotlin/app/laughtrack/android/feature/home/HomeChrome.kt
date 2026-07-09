@file:Suppress("FunctionName")

package app.laughtrack.android.feature.home

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import app.laughtrack.android.core.data.search.SearchShortcut
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import java.util.Locale

@Composable
internal fun DiscoverHeader(onOpenEntity: (AppRoute) -> Unit) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(top = 8.dp, bottom = 0.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        HeaderCircleButton(
            onClick = { onOpenEntity(AppRoute.Profile) },
        ) {
            Icon(
                imageVector = Icons.Filled.Person,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.size(28.dp),
            )
        }

        Row(
            modifier =
                Modifier
                    .weight(1f)
                    .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            PrimitiveChip("Shows")
            PrimitiveChip("Comedians")
            PrimitiveChip("Clubs")
        }

        HeaderCircleButton(
            onClick = { onOpenEntity(AppRoute.Profile) },
        ) {
            Icon(
                imageVector = Icons.Filled.LocationOn,
                contentDescription = null,
                tint = LaughTrackColors.AccentStrong,
                modifier = Modifier.size(27.dp),
            )
        }
    }
}

@Composable
private fun HeaderCircleButton(
    onClick: () -> Unit,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .size(48.dp)
                .clip(CircleShape)
                .clickable(onClick = onClick)
                .border(1.dp, LaughTrackColors.BorderSubtle, CircleShape),
        color = LaughTrackColors.SurfaceElevated.copy(alpha = 0.94f),
        shape = CircleShape,
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center,
        ) {
            content()
        }
    }
}

@Composable
private fun PrimitiveChip(title: String) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = LaughTrackColors.Canvas.copy(alpha = 0.1f),
        modifier =
            Modifier
                .height(34.dp)
                .border(1.dp, LaughTrackColors.AccentMuted, RoundedCornerShape(999.dp)),
    ) {
        Box(
            modifier = Modifier.padding(horizontal = 14.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = title.uppercase(Locale.US),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
            )
        }
    }
}

/**
 * Interactive location header: shows the ZIP/city the feed is scoped to, a manual
 * ZIP field, and a "Use location" button that requests coarse/fine location and
 * reverse-geocodes the device position to a ZIP. Mirrors the iOS HomeView header.
 */
@Composable
internal fun LocationHeader(
    title: String,
    subtitle: String,
    zip: String?,
    isResolving: Boolean,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
) {
    val context = LocalContext.current
    val permissionLauncher =
        rememberLauncherForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions(),
        ) { grants ->
            if (grants.values.any { it }) onUseLocation()
        }

    Surface(
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(12.dp),
        modifier =
            Modifier
                .fillMaxWidth()
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(12.dp)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier =
                        Modifier
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(LaughTrackColors.AccentStrong.copy(alpha = 0.14f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = Icons.Filled.LocationOn,
                        contentDescription = null,
                        tint = LaughTrackColors.AccentStrong,
                        modifier = Modifier.size(19.dp),
                    )
                }
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    Text(title, style = MaterialTheme.typography.titleMedium)
                    Text(
                        subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                var zipText by remember(zip) { mutableStateOf(zip.orEmpty()) }
                OutlinedTextField(
                    value = zipText,
                    onValueChange = { entry ->
                        zipText = entry.filter(Char::isDigit).take(ZIP_LENGTH)
                        if (zipText.length == ZIP_LENGTH) onManualZip(zipText)
                    },
                    label = { Text("ZIP") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.weight(1f),
                )
                Button(
                    onClick = {
                        if (hasLocationPermission(context)) {
                            onUseLocation()
                        } else {
                            permissionLauncher.launch(
                                arrayOf(
                                    Manifest.permission.ACCESS_COARSE_LOCATION,
                                    Manifest.permission.ACCESS_FINE_LOCATION,
                                ),
                            )
                        }
                    },
                    enabled = !isResolving,
                ) {
                    Text(if (isResolving) "Locating…" else "Use location")
                }
            }
        }
    }
}

private fun hasLocationPermission(context: Context): Boolean =
    ContextCompat.checkSelfPermission(
        context,
        Manifest.permission.ACCESS_COARSE_LOCATION,
    ) == PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED

@Composable
internal fun ShortcutRow(onShortcut: (SearchShortcut) -> Unit) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        ShortcutChip("Tonight") { onShortcut(SearchShortcut.TONIGHT) }
        ShortcutChip("This Week") { onShortcut(SearchShortcut.THIS_WEEK) }
        ShortcutChip("Near Me") { onShortcut(SearchShortcut.NEAR_ME) }
    }
}

@Composable
private fun ShortcutChip(
    label: String,
    onClick: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = LaughTrackColors.AccentStrong.copy(alpha = 0.12f),
        modifier =
            Modifier
                .height(36.dp)
                .clip(RoundedCornerShape(999.dp))
                .clickable(onClick = onClick)
                .border(1.dp, LaughTrackColors.AccentMuted, RoundedCornerShape(999.dp)),
    ) {
        Box(
            modifier = Modifier.padding(horizontal = 16.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
            )
        }
    }
}

private const val ZIP_LENGTH = 5
