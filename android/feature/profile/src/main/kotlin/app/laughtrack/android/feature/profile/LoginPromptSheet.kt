@file:OptIn(ExperimentalMaterial3Api::class)

package app.laughtrack.android.feature.profile

import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogWindowProvider
import androidx.core.view.WindowCompat
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.ui.theme.LaughTrackColors

internal enum class LoginPromptProvider {
    Google,
    Apple,
    Email,
}

internal data class LoginPromptOption(
    val provider: LoginPromptProvider,
    val label: String,
    val isPrimary: Boolean,
)

/** Presentation contract kept independent of Compose so provider hierarchy is easy to verify. */
internal val loginPromptOptions =
    listOf(
        LoginPromptOption(LoginPromptProvider.Google, "Continue with Google", isPrimary = true),
        LoginPromptOption(LoginPromptProvider.Apple, "Continue with Apple", isPrimary = false),
        LoginPromptOption(LoginPromptProvider.Email, "Email me a sign-in link", isPrimary = false),
    )

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

    val actions =
        mapOf(
            LoginPromptProvider.Google to { launch(viewModel.buildGoogleSignInUrl()) },
            LoginPromptProvider.Apple to { launch(viewModel.buildAppleSignInUrl()) },
            LoginPromptProvider.Email to { launch(viewModel.buildEmailSignInUrl()) },
        )

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = LaughTrackColors.Surface,
        contentColor = LaughTrackColors.Foreground,
        scrimColor = Color.Black.copy(alpha = 0.76f),
        tonalElevation = 0.dp,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        dragHandle = {
            Spacer(
                Modifier
                    .padding(top = 12.dp)
                    .size(width = 42.dp, height = 4.dp)
                    .background(LaughTrackColors.ForegroundMuted.copy(alpha = 0.5f), CircleShape),
            )
        },
    ) {
        LightSystemBarIconsWhileVisible()
        Column(
            Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        listOf(
                            LaughTrackColors.AccentMuted.copy(alpha = 0.22f),
                            Color.Transparent,
                        ),
                    ),
                ).padding(horizontal = 24.dp)
                .padding(top = 18.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Box(
                    Modifier
                        .size(8.dp)
                        .background(LaughTrackColors.AccentStrong, CircleShape),
                )
                Text(
                    "LAUGHTRACK",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.8.sp,
                    color = LaughTrackColors.AccentStrong,
                )
            }
            Text(
                "Sign in to save favorites",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = LaughTrackColors.Foreground,
            )
            Text(
                "Follow comedians and keep your favorites in sync wherever you watch.",
                style = MaterialTheme.typography.bodyMedium,
                color = LaughTrackColors.ForegroundMuted,
            )
            Spacer(Modifier.height(4.dp))

            loginPromptOptions.forEachIndexed { index, option ->
                if (index == 1) LoginPromptAlternativesDivider()
                LoginPromptProviderButton(
                    option = option,
                    onClick = actions.getValue(option.provider),
                )
            }

            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                Text("Not now", color = LaughTrackColors.ForegroundMuted)
            }
        }
    }
}

@Composable
private fun LoginPromptAlternativesDivider() {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        HorizontalDivider(Modifier.weight(1f), color = LaughTrackColors.BorderSubtle)
        Text(
            "OTHER WAYS TO SIGN IN",
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.ForegroundMuted,
            letterSpacing = 1.sp,
        )
        HorizontalDivider(Modifier.weight(1f), color = LaughTrackColors.BorderSubtle)
    }
}

@Composable
private fun LoginPromptProviderButton(
    option: LoginPromptOption,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        modifier =
            Modifier
                .fillMaxWidth()
                .height(52.dp)
                .then(
                    if (option.isPrimary) {
                        Modifier
                    } else {
                        Modifier.border(1.dp, LaughTrackColors.BorderSubtle, CircleShape)
                    },
                ),
        colors =
            ButtonDefaults.buttonColors(
                containerColor =
                    if (option.isPrimary) {
                        LaughTrackColors.AccentStrong
                    } else {
                        LaughTrackColors.SurfaceElevated
                    },
                contentColor = if (option.isPrimary) Color(0xFF21120C) else LaughTrackColors.Foreground,
            ),
        shape = CircleShape,
    ) {
        Text(option.label, fontWeight = if (option.isPrimary) FontWeight.Bold else FontWeight.Medium)
    }
}

/** ModalBottomSheet owns a dialog window, so set icon contrast on that window, not the activity. */
@Composable
private fun LightSystemBarIconsWhileVisible() {
    val view = LocalView.current
    DisposableEffect(view) {
        val window = (view.parent as? DialogWindowProvider)?.window
        val controller = window?.let { WindowCompat.getInsetsController(it, it.decorView) }
        val previousStatusIcons = controller?.isAppearanceLightStatusBars
        val previousNavigationIcons = controller?.isAppearanceLightNavigationBars

        controller?.isAppearanceLightStatusBars = false
        controller?.isAppearanceLightNavigationBars = false

        onDispose {
            previousStatusIcons?.let { controller?.isAppearanceLightStatusBars = it }
            previousNavigationIcons?.let { controller?.isAppearanceLightNavigationBars = it }
        }
    }
}
