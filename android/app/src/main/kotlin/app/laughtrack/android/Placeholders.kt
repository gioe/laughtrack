package app.laughtrack.android

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Temporary tab body used until the real feature screens land (Favorites →
 * TASK-3261, Notifications → TASK-3264).
 */
@Composable
fun PlaceholderScreen(title: String) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(title, style = MaterialTheme.typography.headlineMedium)
        Text(
            "Coming soon.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/**
 * Temporary account surface on the Profile destination until the real profile/
 * settings screen lands (TASK-3266). Drives the TASK-3257 OAuth + session layer:
 * Google/Apple sign-in via Custom Tabs, sign-out, and delete-account.
 */
@Composable
fun ProfileAuthScreen(
    status: String,
    onGoogleSignIn: () -> Unit,
    onAppleSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onDeleteAccount: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Account", style = MaterialTheme.typography.headlineMedium)
        Text(
            status,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onGoogleSignIn, modifier = Modifier.fillMaxWidth()) {
            Text("Continue with Google")
        }
        Button(onClick = onAppleSignIn, modifier = Modifier.fillMaxWidth()) {
            Text("Continue with Apple")
        }
        OutlinedButton(onClick = onSignOut, modifier = Modifier.fillMaxWidth()) {
            Text("Sign out")
        }
        OutlinedButton(onClick = onDeleteAccount, modifier = Modifier.fillMaxWidth()) {
            Text("Delete account")
        }
    }
}
