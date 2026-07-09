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
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
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
 * Location header, matching the iOS HomeLocationPrompt: a single tappable row
 * (location icon, "Near City, ST" / "ZIP xxxxx" title, source subtitle, trailing
 * chevron). The manual-ZIP field and "Use my location" action live behind the tap
 * in a bottom sheet, mirroring the iOS HomeLocationEditorSheet.
 */
@Composable
internal fun LocationHeader(
    title: String,
    subtitle: String,
    zip: String?,
    distanceMiles: Int,
    isResolving: Boolean,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
    onSetDistance: (Int) -> Unit,
    onClearLocation: () -> Unit,
) {
    // Saveable so an activity recreation while the system permission dialog is up
    // (rotation, process death) re-composes the sheet and its permission launcher,
    // keeping the grant result deliverable.
    var showSheet by rememberSaveable { mutableStateOf(false) }
    val shape = RoundedCornerShape(12.dp)

    Surface(
        color = LaughTrackColors.SurfaceElevated,
        shape = shape,
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(shape)
                .clickable { showSheet = true }
                .border(1.dp, LaughTrackColors.BorderSubtle, shape),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
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
                    if (isResolving) "Locating…" else subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = "Edit location",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(22.dp),
            )
        }
    }

    if (showSheet) {
        LocationEditorSheet(
            zip = zip,
            distanceMiles = distanceMiles,
            isResolving = isResolving,
            onManualZip = onManualZip,
            onUseLocation = onUseLocation,
            onSetDistance = onSetDistance,
            onClearLocation = onClearLocation,
            onDismiss = { showSheet = false },
        )
    }
}

/**
 * Bottom-sheet editor for the Discover location, mirroring the iOS
 * HomeLocationEditorSheet: manual ZIP entry prefilled with the active ZIP
 * (applies once five digits are typed, then dismisses), a distance chip row
 * that applies immediately and keeps the sheet open (iOS chip-picker binding
 * semantics), a "Use my location" button carrying the permission-request flow,
 * and — only while a location is set — a "Clear location" action that reverts
 * to the server-inferred default area. ZIP/location/clear dismiss the sheet;
 * resolution progress reads off the collapsed row's "Locating…" subtitle.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LocationEditorSheet(
    zip: String?,
    distanceMiles: Int,
    isResolving: Boolean,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
    onSetDistance: (Int) -> Unit,
    onClearLocation: () -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current
    val permissionLauncher =
        rememberLauncherForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions(),
        ) { grants ->
            if (grants.values.any { it }) {
                onUseLocation()
                onDismiss()
            }
        }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Set your location",
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                "Choose where Discover looks for shows, clubs, and comedians.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            var zipText by remember(zip) { mutableStateOf(zip.orEmpty()) }
            OutlinedTextField(
                value = zipText,
                onValueChange = { entry ->
                    zipText = entry.filter(Char::isDigit).take(ZIP_LENGTH)
                    // Only a ZIP different from the prefilled active one applies —
                    // otherwise the prefill itself would immediately dismiss the sheet.
                    if (zipText.length == ZIP_LENGTH && zipText != zip) {
                        onManualZip(zipText)
                        onDismiss()
                    }
                },
                label = { Text("ZIP") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )

            Text(
                "DISTANCE",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                DISTANCE_OPTIONS_MILES.forEach { miles ->
                    FilterChip(
                        selected = miles == distanceMiles,
                        onClick = { onSetDistance(miles) },
                        label = { Text("$miles mi") },
                    )
                }
            }

            Button(
                onClick = {
                    if (hasLocationPermission(context)) {
                        onUseLocation()
                        onDismiss()
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
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (isResolving) "Locating…" else "Use my location")
            }

            // Mirrors iOS: the clear action only renders while a location is set.
            if (zip != null) {
                TextButton(
                    onClick = {
                        onClearLocation()
                        onDismiss()
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Clear location")
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

private const val ZIP_LENGTH = 5

// Mirrors iOS NearbyPreferenceStore.distanceOptions so the two clients offer the
// same radius choices.
private val DISTANCE_OPTIONS_MILES = listOf(10, 25, 50, 100)
