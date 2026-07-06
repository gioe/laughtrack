@file:OptIn(ExperimentalMaterial3Api::class)

package app.laughtrack.android.feature.profile

import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

/**
 * Bottom-sheet sign-in prompt shown when a signed-out user taps a gated action
 * (favoriting). Reuses [ProfileViewModel]'s OAuth / magic-link URL builders and
 * the same Custom Tabs flow as the Profile screen, so a completed sign-in flows
 * back through the shared laughtrack:// callback. Mirrors iOS
 * LaughTrackLoginModalView.
 */
@Composable
fun LoginPromptSheet(
    onDismiss: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val context = LocalContext.current

    fun launch(url: String) {
        CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
    }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Sign in to save favorites",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                "Create a free LaughTrack account to follow comedians and sync your favorites across devices.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(onClick = { launch(viewModel.buildGoogleSignInUrl()) }, modifier = Modifier.fillMaxWidth()) {
                Text("Continue with Google")
            }
            OutlinedButton(onClick = { launch(viewModel.buildAppleSignInUrl()) }, modifier = Modifier.fillMaxWidth()) {
                Text("Continue with Apple")
            }
            OutlinedButton(onClick = { launch(viewModel.buildEmailSignInUrl()) }, modifier = Modifier.fillMaxWidth()) {
                Text("Email me a sign-in link")
            }
            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                Text("Not now")
            }
        }
    }
}
