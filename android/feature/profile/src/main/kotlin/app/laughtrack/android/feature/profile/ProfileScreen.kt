@file:OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)

package app.laughtrack.android.feature.profile

import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.data.profile.ProfileAccount
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.ui.components.RemoteImage

@Composable
fun ProfileScreen(
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    if (state.showDeleteConfirmation) {
        AlertDialog(
            onDismissRequest = viewModel::dismissDeleteAccount,
            title = { Text("Delete your LaughTrack account?") },
            text = { Text("This permanently removes your account and saved favorites. This cannot be undone.") },
            confirmButton = {
                TextButton(
                    enabled = !state.isMutating,
                    onClick = viewModel::deleteAccount,
                ) {
                    Text("Delete account")
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissDeleteAccount) {
                    Text("Cancel")
                }
            },
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineLarge)

        if (state.isLoading) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                CircularProgressIndicator()
            }
        }

        if (state.message != null) {
            AssistChip(
                onClick = viewModel::clearMessage,
                label = { Text(state.message.orEmpty()) },
            )
        }

        AccountCard(
            signedIn = state.signedIn,
            account = state.account,
            isMutating = state.isMutating,
            onGoogleSignIn = {
                CustomTabsIntent.Builder()
                    .build()
                    .launchUrl(context, Uri.parse(viewModel.buildGoogleSignInUrl()))
            },
            onAppleSignIn = {
                CustomTabsIntent.Builder()
                    .build()
                    .launchUrl(context, Uri.parse(viewModel.buildAppleSignInUrl()))
            },
            onSignOut = viewModel::signOut,
            onDeleteAccount = viewModel::requestDeleteAccount,
        )

        if (state.signedIn) {
            LocationSection(
                preferences = state.preferences,
                zipCodeDraft = state.zipCodeDraft,
                selectedDistanceMiles = state.selectedDistanceMiles,
                isMutating = state.isMutating,
                onZipChange = viewModel::setZipCodeDraft,
                onDistanceChange = viewModel::setSelectedDistance,
                onSave = viewModel::saveLocation,
                onClear = viewModel::clearLocation,
            )
            NotificationsSection(
                preferences = state.preferences,
                enabled = !state.isMutating,
                onEmailChange = viewModel::setEmailNotifications,
                onPushChange = viewModel::setPushNotifications,
            )
        } else {
            GuestPreview()
        }
    }
}

@Composable
private fun AccountCard(
    signedIn: Boolean,
    account: ProfileAccount?,
    isMutating: Boolean,
    onGoogleSignIn: () -> Unit,
    onAppleSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
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
            }
        }
    }
}

@Composable
private fun Avatar(url: String?, signedIn: Boolean) {
    Box(
        modifier = Modifier
            .size(56.dp)
            .clip(CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        if (url != null) {
            RemoteImage(
                url = url,
                contentDescription = "Profile photo",
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Icon(
                imageVector = Icons.Filled.Person,
                contentDescription = null,
                modifier = Modifier.size(40.dp),
                tint = if (signedIn) {
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
    onZipChange: (String) -> Unit,
    onDistanceChange: (Int) -> Unit,
    onSave: () -> Unit,
    onClear: () -> Unit,
) {
    SettingsSection(title = "Location") {
        Text(
            text = if (preferences.zipCode == null) {
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
            enabled = !isMutating,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Save profile location")
        }
        if (preferences.zipCode != null) {
            OutlinedButton(
                onClick = onClear,
                enabled = !isMutating,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Clear profile location")
            }
        }
    }
}

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
    content: @Composable Column.() -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            title,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Card(modifier = Modifier.fillMaxWidth()) {
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
