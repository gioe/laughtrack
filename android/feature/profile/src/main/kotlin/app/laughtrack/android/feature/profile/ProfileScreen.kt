@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.laughtrack.android.feature.profile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.data.profile.ProfileAccount
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback

internal enum class ProfileLayoutMode {
    Compact,
    Expanded,
}

internal data class ProfileAdaptiveLayoutSpec(
    val mode: ProfileLayoutMode,
    val contentMaxWidth: Dp,
    val horizontalPadding: Dp,
    val paneSpacing: Dp,
    val accountPaneWidth: Dp,
    val centerContentVertically: Boolean,
)

private val PROFILE_EXPANDED_BREAKPOINT = 600.dp
private val PROFILE_WIDE_BREAKPOINT = 720.dp
private val PROFILE_SEVEN_INCH_CONTENT_MAX_WIDTH = 560.dp
private val PROFILE_EXPANDED_CONTENT_MAX_WIDTH = 720.dp

internal fun profileAdaptiveLayoutSpec(availableWidth: Dp): ProfileAdaptiveLayoutSpec {
    if (availableWidth < PROFILE_EXPANDED_BREAKPOINT) {
        return ProfileAdaptiveLayoutSpec(
            mode = ProfileLayoutMode.Compact,
            contentMaxWidth = Dp.Infinity,
            horizontalPadding = 24.dp,
            paneSpacing = 18.dp,
            accountPaneWidth = Dp.Infinity,
            centerContentVertically = false,
        )
    }

    val isWide = availableWidth >= PROFILE_WIDE_BREAKPOINT
    val contentMaxWidth =
        if (isWide) PROFILE_EXPANDED_CONTENT_MAX_WIDTH else PROFILE_SEVEN_INCH_CONTENT_MAX_WIDTH
    val boundedWidth = minOf(availableWidth, contentMaxWidth)
    return ProfileAdaptiveLayoutSpec(
        mode = ProfileLayoutMode.Expanded,
        contentMaxWidth = contentMaxWidth,
        horizontalPadding = if (isWide) 32.dp else 8.dp,
        paneSpacing = if (isWide) 32.dp else 12.dp,
        accountPaneWidth = (boundedWidth * 0.42f).coerceIn(264.dp, 360.dp),
        centerContentVertically = true,
    )
}

@Composable
fun ProfileScreen(viewModel: ProfileViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val permissionLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
            viewModel.useCurrentLocation()
        }

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    ProfileContent(
        state = state,
        actions =
            ProfileActions(
                dismissDeleteAccount = viewModel::dismissDeleteAccount,
                deleteAccount = viewModel::deleteAccount,
                clearMessage = viewModel::clearMessage,
                googleSignIn = { launchSignIn(context, viewModel.buildGoogleSignInUrl()) },
                appleSignIn = { launchSignIn(context, viewModel.buildAppleSignInUrl()) },
                emailSignIn = { launchSignIn(context, viewModel.buildEmailSignInUrl()) },
                signOut = viewModel::signOut,
                requestDeleteAccount = viewModel::requestDeleteAccount,
                setZipCodeDraft = viewModel::setZipCodeDraft,
                setSelectedDistance = viewModel::setSelectedDistance,
                saveLocation = viewModel::saveLocation,
                useCurrentLocation = {
                    if (hasLocationPermission(context)) {
                        viewModel.useCurrentLocation()
                    } else {
                        permissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_COARSE_LOCATION,
                                Manifest.permission.ACCESS_FINE_LOCATION,
                            ),
                        )
                    }
                },
                clearLocation = viewModel::clearLocation,
                setEmailNotifications = viewModel::setEmailNotifications,
                setPushNotifications = viewModel::setPushNotifications,
            ),
    )
}

/** Render the real profile UI from deterministic state without creating a Hilt ViewModel. */
@Composable
fun ProfileScreen(stateOverride: ProfileUiState) {
    ProfileContent(state = stateOverride, actions = ProfileActions())
}

private fun launchSignIn(
    context: android.content.Context,
    url: String,
) {
    CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
}

private data class ProfileActions(
    val dismissDeleteAccount: () -> Unit = {},
    val deleteAccount: () -> Unit = {},
    val clearMessage: () -> Unit = {},
    val googleSignIn: () -> Unit = {},
    val appleSignIn: () -> Unit = {},
    val emailSignIn: () -> Unit = {},
    val signOut: () -> Unit = {},
    val requestDeleteAccount: () -> Unit = {},
    val setZipCodeDraft: (String) -> Unit = {},
    val setSelectedDistance: (Int) -> Unit = {},
    val saveLocation: () -> Unit = {},
    val useCurrentLocation: () -> Unit = {},
    val clearLocation: () -> Unit = {},
    val setEmailNotifications: (Boolean) -> Unit = {},
    val setPushNotifications: (Boolean) -> Unit = {},
)

@Composable
private fun ProfileContent(
    state: ProfileUiState,
    actions: ProfileActions,
) {
    if (state.showDeleteConfirmation) {
        AlertDialog(
            onDismissRequest = actions.dismissDeleteAccount,
            title = { Text("Delete your LaughTrack account?") },
            text = { Text("This permanently removes your account and saved favorites. This cannot be undone.") },
            confirmButton = {
                TextButton(
                    enabled = !state.isMutating,
                    onClick = actions.deleteAccount,
                ) {
                    Text("Delete account")
                }
            },
            dismissButton = {
                TextButton(onClick = actions.dismissDeleteAccount) {
                    Text("Cancel")
                }
            },
        )
    }

    val scrollState = rememberScrollState()
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val layoutSpec = profileAdaptiveLayoutSpec(maxWidth)
        Column(
            modifier =
                Modifier
                    .align(Alignment.TopCenter)
                    .widthIn(max = layoutSpec.contentMaxWidth)
                    .fillMaxSize()
                    .verticalScroll(scrollState)
                    .padding(horizontal = layoutSpec.horizontalPadding, vertical = 24.dp),
            verticalArrangement =
                if (layoutSpec.centerContentVertically) {
                    Arrangement.spacedBy(18.dp, Alignment.CenterVertically)
                } else {
                    Arrangement.spacedBy(18.dp)
                },
        ) {
            if (state.isLoading) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                    CircularProgressIndicator()
                }
            }

            if (state.message != null) {
                AssistChip(
                    onClick = actions.clearMessage,
                    label = { Text(state.message.orEmpty()) },
                )
            }

            when (layoutSpec.mode) {
                ProfileLayoutMode.Compact -> ProfileCompactContent(state, actions)
                ProfileLayoutMode.Expanded ->
                    ProfileExpandedContent(
                        state = state,
                        actions = actions,
                        accountPaneWidth = layoutSpec.accountPaneWidth,
                        paneSpacing = layoutSpec.paneSpacing,
                    )
            }
        }
    }
}

@Composable
private fun ProfileCompactContent(
    state: ProfileUiState,
    actions: ProfileActions,
) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        ProfileAccountCard(state, actions)
        ProfileSettings(state, actions)
    }
}

@Composable
private fun ProfileExpandedContent(
    state: ProfileUiState,
    actions: ProfileActions,
    accountPaneWidth: Dp,
    paneSpacing: Dp,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(paneSpacing),
        verticalAlignment = Alignment.Top,
    ) {
        Column(
            modifier = Modifier.width(accountPaneWidth),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            ProfileAccountCard(state, actions)
            if (state.signedIn) {
                NotificationsSection(
                    preferences = state.preferences,
                    enabled = !state.isMutating,
                    onEmailChange = actions.setEmailNotifications,
                    onPushChange = actions.setPushNotifications,
                )
            }
        }
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            if (state.signedIn) {
                ProfileLocationSection(state, actions)
            } else {
                GuestPreview()
            }
        }
    }
}

@Composable
private fun ProfileAccountCard(
    state: ProfileUiState,
    actions: ProfileActions,
) {
    AccountCard(
        signedIn = state.signedIn,
        account = state.account,
        isMutating = state.isMutating,
        onGoogleSignIn = actions.googleSignIn,
        onAppleSignIn = actions.appleSignIn,
        onEmailSignIn = actions.emailSignIn,
        onSignOut = actions.signOut,
        onDeleteAccount = actions.requestDeleteAccount,
    )
}

@Composable
private fun ProfileSettings(
    state: ProfileUiState,
    actions: ProfileActions,
) {
    if (state.signedIn) {
        ProfileLocationSection(state, actions)
        NotificationsSection(
            preferences = state.preferences,
            enabled = !state.isMutating,
            onEmailChange = actions.setEmailNotifications,
            onPushChange = actions.setPushNotifications,
        )
    } else {
        GuestPreview()
    }
}

@Composable
private fun ProfileLocationSection(
    state: ProfileUiState,
    actions: ProfileActions,
) {
    LocationSection(
        preferences = state.preferences,
        zipCodeDraft = state.zipCodeDraft,
        selectedDistanceMiles = state.selectedDistanceMiles,
        isMutating = state.isMutating,
        isResolvingCurrentLocation = state.isResolvingCurrentLocation,
        onZipChange = actions.setZipCodeDraft,
        onDistanceChange = actions.setSelectedDistance,
        onSave = actions.saveLocation,
        onUseCurrentLocation = actions.useCurrentLocation,
        onClear = actions.clearLocation,
    )
}

@Composable
private fun AccountCard(
    signedIn: Boolean,
    account: ProfileAccount?,
    isMutating: Boolean,
    onGoogleSignIn: () -> Unit,
    onAppleSignIn: () -> Unit,
    onEmailSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Avatar(account?.avatarUrl, signedIn)
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = account?.displayName ?: if (signedIn) "LaughTrack account" else "Guest mode",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = account?.email ?: "Sign in to save favorites and profile preferences.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }

            if (signedIn) {
                OutlinedButton(
                    onClick = onSignOut,
                    enabled = !isMutating,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Sign out")
                }
                TextButton(
                    onClick = onDeleteAccount,
                    enabled = !isMutating,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Delete account")
                }
            } else {
                Button(onClick = onGoogleSignIn, modifier = Modifier.fillMaxWidth()) {
                    Text("Continue with Google")
                }
                OutlinedButton(onClick = onAppleSignIn, modifier = Modifier.fillMaxWidth()) {
                    Text("Continue with Apple")
                }
                OutlinedButton(onClick = onEmailSignIn, modifier = Modifier.fillMaxWidth()) {
                    Text("Email me a sign-in link")
                }
            }
        }
    }
}

@Composable
private fun Avatar(
    url: String?,
    signedIn: Boolean,
) {
    Box(
        modifier =
            Modifier
                .size(56.dp)
                .clip(CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        if (url != null) {
            RemoteImage(
                url = url,
                fallback = RemoteImageFallback.Person,
                contentDescription = "Profile photo",
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Icon(
                imageVector = Icons.Filled.Person,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint =
                    if (signedIn) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
            )
        }
    }
}

@Composable
private fun LocationSection(
    preferences: ProfilePreferences,
    zipCodeDraft: String,
    selectedDistanceMiles: Int,
    isMutating: Boolean,
    isResolvingCurrentLocation: Boolean,
    onZipChange: (String) -> Unit,
    onDistanceChange: (Int) -> Unit,
    onSave: () -> Unit,
    onUseCurrentLocation: () -> Unit,
    onClear: () -> Unit,
) {
    SettingsSection(title = "Location") {
        Text(
            text =
                if (preferences.zipCode == null) {
                    "No profile location is saved. Enter a ZIP code to power Near Me."
                } else {
                    "Near Me is using ZIP ${preferences.zipCode} from your profile."
                },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = zipCodeDraft,
            onValueChange = onZipChange,
            label = { Text("ZIP code") },
            placeholder = { Text("10012") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            text = "Distance",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            distanceOptions.forEach { distance ->
                FilterChip(
                    selected = selectedDistanceMiles == distance,
                    onClick = { onDistanceChange(distance) },
                    label = { Text("$distance mi") },
                )
            }
        }
        Button(
            onClick = onSave,
            enabled = !isMutating && !isResolvingCurrentLocation,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Save profile location")
        }
        OutlinedButton(
            onClick = onUseCurrentLocation,
            enabled = !isMutating && !isResolvingCurrentLocation,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (isResolvingCurrentLocation) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                )
                Text(" Finding ZIP…")
            } else {
                Text("Use current location")
            }
        }
        if (preferences.zipCode != null) {
            OutlinedButton(
                onClick = onClear,
                enabled = !isMutating && !isResolvingCurrentLocation,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Clear profile location")
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
private fun NotificationsSection(
    preferences: ProfilePreferences,
    enabled: Boolean,
    onEmailChange: (Boolean) -> Unit,
    onPushChange: (Boolean) -> Unit,
) {
    SettingsSection(title = "Notifications") {
        Text(
            "Pick how you'd like to hear about nearby shows from your favorite comedians.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        NotificationRow(
            title = "Email",
            checked = preferences.emailShowNotifications,
            enabled = enabled,
            onCheckedChange = onEmailChange,
        )
        NotificationRow(
            title = "Push notifications",
            checked = preferences.pushShowNotifications,
            enabled = enabled,
            onCheckedChange = onPushChange,
        )
        Text(
            "Alert preferences are saved to your profile.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun NotificationRow(
    title: String,
    checked: Boolean,
    enabled: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.weight(1f),
        )
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            enabled = enabled,
        )
    }
}

@Composable
private fun SettingsSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            title,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground,
            fontWeight = FontWeight.SemiBold,
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                content = content,
            )
        }
    }
}

@Composable
private fun GuestPreview() {
    SettingsSection(title = "Preview") {
        Text(
            "Profile settings are available after sign-in.",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
        )
        Text(
            "Use a saved ZIP code for Near Me and choose email or push alerts for favorite comedians.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private val distanceOptions = listOf(10, 25, 50, 100)
