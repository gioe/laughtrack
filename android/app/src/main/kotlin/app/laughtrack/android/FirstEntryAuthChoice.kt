package app.laughtrack.android

import android.content.Context
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.ui.components.LaughTrackAtmosphereBackground
import app.laughtrack.android.feature.profile.ProfileViewModel

internal const val FIRST_ENTRY_AUTH_CHOICE_TEST_TAG = "first-entry-auth-choice"

/** Root surfaces shown while the app resolves its first-entry authentication choice. */
internal enum class FirstEntryRootSurface {
    Loading,
    AuthChoice,
    AppShell,
}

/**
 * Keep the first-entry gate outside navigation chrome, matching iOS. Session restoration must
 * finish before a signed-out surface is selected or returning users briefly see the auth gate.
 */
internal fun firstEntryRootSurface(
    sessionRestoreCompleted: Boolean,
    signedIn: Boolean,
    hasResolvedFirstEntryChoice: Boolean,
): FirstEntryRootSurface =
    when {
        !sessionRestoreCompleted -> FirstEntryRootSurface.Loading
        signedIn || hasResolvedFirstEntryChoice -> FirstEntryRootSurface.AppShell
        else -> FirstEntryRootSurface.AuthChoice
    }

/** Persists whether this install has chosen guest browsing or completed sign-in. */
internal class FirstEntryAuthChoiceStore(
    initialResolved: Boolean,
    private val persistResolved: () -> Unit,
) {
    var hasResolvedFirstEntryChoice: Boolean = initialResolved
        private set

    fun continueAsGuest() = markResolved()

    fun markSignedIn() = markResolved()

    private fun markResolved() {
        if (hasResolvedFirstEntryChoice) return
        hasResolvedFirstEntryChoice = true
        persistResolved()
    }

    companion object {
        private const val PREFERENCES_NAME = "first_entry_auth_choice"
        private const val RESOLVED_KEY = "has_resolved_first_entry_choice"

        fun create(context: Context): FirstEntryAuthChoiceStore {
            val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
            return FirstEntryAuthChoiceStore(
                initialResolved = preferences.getBoolean(RESOLVED_KEY, false),
                persistResolved = { preferences.edit().putBoolean(RESOLVED_KEY, true).apply() },
            )
        }
    }
}

@Composable
internal fun FirstEntryLoadingScreen() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        LaughTrackAtmosphereBackground()
        CircularProgressIndicator()
    }
}

/** Full-screen first-launch choice. Protected guest actions continue to use LoginPromptSheet. */
@Composable
internal fun FirstEntryAuthChoiceScreen(
    onContinueAsGuest: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val context = LocalContext.current
    FirstEntryAuthChoiceContent(
        onContinueAsGuest = onContinueAsGuest,
        onGoogleSignIn = { launchSignIn(context, viewModel.buildGoogleSignInUrl()) },
        onAppleSignIn = { launchSignIn(context, viewModel.buildAppleSignInUrl()) },
        onEmailSignIn = { launchSignIn(context, viewModel.buildEmailSignInUrl()) },
    )
}

@Composable
private fun FirstEntryAuthChoiceContent(
    onContinueAsGuest: () -> Unit,
    onGoogleSignIn: () -> Unit,
    onAppleSignIn: () -> Unit,
    onEmailSignIn: () -> Unit,
) {
    Box(
        modifier =
            Modifier
                .fillMaxSize()
                .testTag(FIRST_ENTRY_AUTH_CHOICE_TEST_TAG),
        contentAlignment = Alignment.Center,
    ) {
        LaughTrackAtmosphereBackground()
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .windowInsetsPadding(WindowInsets.safeDrawing)
                    .padding(horizontal = 24.dp, vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Box(
                    modifier =
                        Modifier
                            .size(104.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        "LT",
                        style = MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    repeat(5) { index ->
                        val alpha = if (index == 2) 1f else 0.45f
                        Spacer(
                            Modifier
                                .size(if (index == 2) 7.dp else 5.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary.copy(alpha = alpha)),
                        )
                    }
                }

                Text(
                    "LIVE COMEDY NEAR YOU",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    "Find your next laugh",
                    style = MaterialTheme.typography.displaySmall,
                    fontWeight = FontWeight.Black,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )
                Text(
                    "Tonight's lineups, hometown clubs, and the comics you follow — all in one place.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White.copy(alpha = 0.72f),
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(6.dp))
                Button(onClick = onContinueAsGuest, modifier = Modifier.fillMaxWidth()) {
                    Text("Continue as guest")
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    HorizontalDivider(modifier = Modifier.weight(1f), color = Color.White.copy(alpha = 0.2f))
                    Text(
                        "or sign in to sync favorites & alerts",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White.copy(alpha = 0.65f),
                    )
                    HorizontalDivider(modifier = Modifier.weight(1f), color = Color.White.copy(alpha = 0.2f))
                }

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

private fun launchSignIn(
    context: Context,
    url: String,
) {
    CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
}
