package app.laughtrack.android

import android.content.Context
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import app.laughtrack.android.core.ui.components.LaughTrackAtmosphereBackground
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.profile.ProfileViewModel

internal const val FIRST_ENTRY_AUTH_CHOICE_TEST_TAG = "first-entry-auth-choice"
internal const val FIRST_ENTRY_BRAND_LOGO_CONTENT_DESCRIPTION = "LaughTrack microphone logo"

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
    ) {
        FirstEntrySpotlightBackground()
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val compact = maxHeight < 760.dp
            Box(
                modifier =
                    Modifier
                        .fillMaxSize()
                        .windowInsetsPadding(WindowInsets.safeDrawing)
                        .padding(horizontal = 24.dp, vertical = if (compact) 16.dp else 28.dp),
                contentAlignment = Alignment.TopCenter,
            ) {
                Column(
                    modifier = Modifier.fillMaxHeight().fillMaxWidth().widthIn(max = 520.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Spacer(Modifier.weight(1f))

                    FirstEntryBrandLockup(compact = compact)

                    Row(
                        modifier = Modifier.padding(top = if (compact) 12.dp else 20.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        repeat(5) { index ->
                            val distanceFromCenter = kotlin.math.abs(index - 2)
                            Spacer(
                                Modifier
                                    .size(if (index == 2) 7.dp else 5.dp)
                                    .clip(CircleShape)
                                    .background(
                                        LaughTrackColors.AccentStrong.copy(
                                            alpha = 1f - (distanceFromCenter * 0.28f),
                                        ),
                                    ),
                            )
                        }
                    }

                    Column(
                        modifier = Modifier.padding(top = if (compact) 14.dp else 22.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(
                            "LIVE COMEDY NEAR YOU",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 3.2.sp,
                            color = LaughTrackColors.AccentStrong,
                        )
                        Text(
                            buildAnnotatedString {
                                append("Find your next ")
                                withStyle(SpanStyle(color = LaughTrackColors.AccentStrong)) {
                                    append("laugh")
                                }
                            },
                            style = MaterialTheme.typography.displaySmall,
                            fontWeight = FontWeight.Black,
                            color = LaughTrackColors.Foreground,
                            textAlign = TextAlign.Center,
                        )
                        Text(
                            "Tonight's lineups, hometown clubs, and the comics you follow — all in one place.",
                            style = MaterialTheme.typography.bodyLarge,
                            color = LaughTrackColors.ForegroundMuted,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(horizontal = 16.dp),
                        )
                    }

                    Spacer(Modifier.weight(1f))

                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        FirstEntryGuestButton(onClick = onContinueAsGuest)

                        FirstEntrySignInDivider(
                            modifier = Modifier.padding(vertical = 4.dp),
                        )

                        FirstEntryProviderButton(
                            label = "Continue with Apple",
                            light = true,
                            onClick = onAppleSignIn,
                        )
                        FirstEntryProviderButton(
                            label = "Continue with Google",
                            onClick = onGoogleSignIn,
                        )
                        FirstEntryProviderButton(
                            label = "Email me a sign-in link",
                            onClick = onEmailSignIn,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun FirstEntrySpotlightBackground() {
    Canvas(
        Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(LaughTrackColors.Canvas, Color(0xFF090706)),
                ),
            ),
    ) {
        drawRect(
            brush =
                Brush.radialGradient(
                    colors =
                        listOf(
                            LaughTrackColors.AccentStrong.copy(alpha = 0.30f),
                            LaughTrackColors.AccentMuted.copy(alpha = 0.12f),
                            Color.Transparent,
                        ),
                    center = Offset(size.width * 0.5f, size.height * 0.26f),
                    radius = size.minDimension * 0.82f,
                ),
        )

        val cone =
            Path().apply {
                moveTo(size.width * 0.40f, -48f)
                lineTo(size.width * 0.60f, -48f)
                lineTo(size.width * 1.05f, size.height * 0.58f)
                lineTo(size.width * -0.05f, size.height * 0.58f)
                close()
            }
        drawPath(
            path = cone,
            brush =
                Brush.verticalGradient(
                    listOf(Color(0xFFFFD9A3).copy(alpha = 0.12f), Color.Transparent),
                    endY = size.height * 0.58f,
                ),
        )
        drawRect(
            brush =
                Brush.radialGradient(
                    colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.52f)),
                    center = center,
                    radius = size.maxDimension * 0.72f,
                ),
        )
    }
}

@Composable
private fun FirstEntryBrandLockup(compact: Boolean) {
    val glowSize = if (compact) 164.dp else 190.dp
    val logoSize = if (compact) 128.dp else 148.dp

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier =
                Modifier
                    .size(glowSize)
                    .background(
                        Brush.radialGradient(
                            listOf(LaughTrackColors.AccentStrong.copy(alpha = 0.34f), Color.Transparent),
                        ),
                        CircleShape,
                    ),
            contentAlignment = Alignment.Center,
        ) {
            Image(
                painter = painterResource(R.mipmap.ic_launcher_foreground),
                contentDescription = FIRST_ENTRY_BRAND_LOGO_CONTENT_DESCRIPTION,
                modifier =
                    Modifier
                        .size(logoSize)
                        .shadow(24.dp, CircleShape, ambientColor = LaughTrackColors.AccentStrong)
                        .clip(CircleShape)
                        .border(1.dp, LaughTrackColors.AccentStrong.copy(alpha = 0.35f), CircleShape),
            )
        }
        Text(
            "LaughTrack",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Black,
            letterSpacing = 0.4.sp,
            color = LaughTrackColors.Foreground,
        )
    }
}

@Composable
private fun FirstEntryGuestButton(onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier =
            Modifier
                .fillMaxWidth()
                .height(54.dp)
                .clip(CircleShape)
                .background(
                    Brush.linearGradient(
                        listOf(LaughTrackColors.AccentStrong, Color(0xFFE27A43)),
                    ),
                ),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = Color.Transparent,
                contentColor = Color(0xFF21120C),
            ),
        shape = CircleShape,
    ) {
        Text("Continue as guest", fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.size(8.dp))
        Icon(
            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
            contentDescription = null,
            modifier = Modifier.size(18.dp),
        )
    }
}

@Composable
private fun FirstEntrySignInDivider(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        HorizontalDivider(modifier = Modifier.weight(1f), color = LaughTrackColors.BorderSubtle)
        Text(
            "or sign in to sync favorites & alerts",
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.ForegroundMuted,
            maxLines = 1,
        )
        HorizontalDivider(modifier = Modifier.weight(1f), color = LaughTrackColors.BorderSubtle)
    }
}

@Composable
private fun FirstEntryProviderButton(
    label: String,
    light: Boolean = false,
    onClick: () -> Unit,
) {
    val container = if (light) LaughTrackColors.Foreground else LaughTrackColors.SurfaceElevated
    val content = if (light) LaughTrackColors.Canvas else LaughTrackColors.Foreground
    Button(
        onClick = onClick,
        modifier =
            Modifier
                .fillMaxWidth()
                .height(50.dp)
                .then(
                    if (light) {
                        Modifier
                    } else {
                        Modifier.border(1.dp, LaughTrackColors.BorderSubtle, CircleShape)
                    },
                ),
        colors = ButtonDefaults.buttonColors(containerColor = container, contentColor = content),
        shape = CircleShape,
    ) {
        Text(label, fontWeight = FontWeight.Medium)
    }
}

private fun launchSignIn(
    context: Context,
    url: String,
) {
    CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(url))
}
