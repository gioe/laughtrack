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
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
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
    isResolving: Boolean,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
) {
    var showSheet by remember { mutableStateOf(false) }
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
            isResolving = isResolving,
            onManualZip = onManualZip,
            onUseLocation = onUseLocation,
            onDismiss = { showSheet = false },
        )
    }
}

/**
 * Bottom-sheet editor for the Discover location: manual ZIP entry (applies once
 * five digits are typed, then dismisses) and a "Use my location" button carrying
 * the permission-request flow that previously lived inline on the Home surface.
 * Both actions dismiss the sheet immediately; resolution progress reads off the
 * collapsed row's "Locating…" subtitle.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LocationEditorSheet(
    zip: String?,
    isResolving: Boolean,
    onManualZip: (String) -> Unit,
    onUseLocation: () -> Unit,
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
                    if (zipText.length == ZIP_LENGTH) {
                        onManualZip(zipText)
                        onDismiss()
                    }
                },
                label = { Text("ZIP") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )

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
