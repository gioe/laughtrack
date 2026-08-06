package app.laughtrack.android.feature.onboarding.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.RemoteImageFallback
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import kotlin.math.roundToInt

internal enum class ComedianOnboardingLayoutMode {
    Compact,
    Expanded,
}

internal data class ComedianOnboardingLayoutSpec(
    val mode: ComedianOnboardingLayoutMode,
    val contentMaxWidth: Dp,
    val horizontalPadding: Dp,
    val sectionSpacing: Dp,
    val cardMaxWidth: Dp,
    val posterSize: Dp,
    val actionSpacing: Dp,
)

private val ONBOARDING_EXPANDED_BREAKPOINT = 600.dp
private val ONBOARDING_WIDE_BREAKPOINT = 800.dp
private val ONBOARDING_SEVEN_INCH_CONTENT_MAX_WIDTH = 560.dp
private val ONBOARDING_EXPANDED_CONTENT_MAX_WIDTH = 620.dp

internal fun comedianOnboardingLayoutSpec(availableWidth: Dp): ComedianOnboardingLayoutSpec {
    if (availableWidth < ONBOARDING_EXPANDED_BREAKPOINT) {
        return ComedianOnboardingLayoutSpec(
            mode = ComedianOnboardingLayoutMode.Compact,
            contentMaxWidth = Dp.Infinity,
            horizontalPadding = 16.dp,
            sectionSpacing = 14.dp,
            cardMaxWidth = Dp.Infinity,
            posterSize = 220.dp,
            actionSpacing = 22.dp,
        )
    }

    val isWide = availableWidth >= ONBOARDING_WIDE_BREAKPOINT
    return ComedianOnboardingLayoutSpec(
        mode = ComedianOnboardingLayoutMode.Expanded,
        contentMaxWidth =
            if (isWide) ONBOARDING_EXPANDED_CONTENT_MAX_WIDTH else ONBOARDING_SEVEN_INCH_CONTENT_MAX_WIDTH,
        horizontalPadding = if (isWide) 32.dp else 24.dp,
        sectionSpacing = if (isWide) 20.dp else 18.dp,
        cardMaxWidth = if (isWide) 520.dp else 480.dp,
        posterSize = if (isWide) 260.dp else 240.dp,
        actionSpacing = if (isWide) 28.dp else 24.dp,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComedianOnboardingScreen(
    onComplete: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ComedianOnboardingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val notificationPermissionLauncher =
        rememberLauncherForActivityResult(
            ActivityResultContracts.RequestPermission(),
        ) { granted ->
            viewModel.onPushPermissionResult(granted)
        }

    LaunchedEffect(state.isComplete) {
        if (state.isComplete) onComplete()
    }

    if (state.showSoftPushPrompt) {
        AlertDialog(
            onDismissRequest = viewModel::deferSoftPushPrompt,
            title = { Text("Get show alerts?") },
            text = { Text("LaughTrack can let you know when comedians you follow add shows near you.") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.softPushEnableTapped()
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else {
                            viewModel.dismissSoftPushPrompt()
                        }
                    },
                ) {
                    Text("Enable")
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::deferSoftPushPrompt) {
                    Text("Maybe later")
                }
            },
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        containerColor = Color.Transparent,
        bottomBar = {
            ContinueBar(
                isSaving = state.isSaving,
                onContinue = viewModel::continueOnboarding,
            )
        },
    ) { padding ->
        BoxWithConstraints(
            Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            val layoutSpec = comedianOnboardingLayoutSpec(maxWidth)
            Column(
                Modifier
                    .align(Alignment.TopCenter)
                    .widthIn(max = layoutSpec.contentMaxWidth)
                    .fillMaxSize()
                    .padding(horizontal = layoutSpec.horizontalPadding, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(layoutSpec.sectionSpacing),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                OnboardingMarqueeHeader(
                    favoriteCount = state.favoriteCount,
                    isSaving = state.isSaving,
                    onSkip = viewModel::continueOnboarding,
                )
                SearchBox(
                    query = state.searchQuery,
                    isSearchMode = state.isSearchMode,
                    onQuery = viewModel::search,
                )
                state.errorMessage?.let {
                    Text(it, color = MaterialTheme.colorScheme.error)
                }

                Box(Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.TopCenter) {
                    when {
                        state.isLoading && state.visibleComedians.isEmpty() -> CircularProgressIndicator()
                        state.isSearchMode ->
                            SearchResults(
                                comedians = state.searchResults,
                                favorites = state.favorites,
                                onFavorite = viewModel::toggleFavorite,
                            )
                        else ->
                            SwipeDeck(
                                comedians = state.suggestions,
                                favorites = state.favorites,
                                passed = state.passed,
                                canRewind = state.passHistory.isNotEmpty(),
                                layoutSpec = layoutSpec,
                                onFavorite = viewModel::toggleFavorite,
                                onPass = viewModel::passComedian,
                                onRewind = viewModel::rewindLastPass,
                                onMore = viewModel::loadMoreSuggestions,
                            )
                    }
                }
            }
        }
    }
}

@Composable
private fun OnboardingMarqueeHeader(
    favoriteCount: Int,
    isSaving: Boolean,
    onSkip: () -> Unit,
) {
    Box(Modifier.fillMaxWidth()) {
        TextButton(
            onClick = onSkip,
            enabled = !isSaving,
            modifier = Modifier.align(Alignment.TopEnd),
        ) {
            Text("Skip")
        }

        Column(
            modifier = Modifier.fillMaxWidth().padding(top = 34.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                "WELCOME TO LAUGHTRACK",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 2.2.sp,
                color = LaughTrackColors.AccentStrong,
            )
            Text(
                "PICK COMEDIANS TO FOLLOW",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Black,
                letterSpacing = 0.4.sp,
                textAlign = TextAlign.Center,
                color = LaughTrackColors.Foreground,
            )
            Text(
                "Swipe right to follow, left to pass — or search for anyone. " +
                    "Aim for 3 so LaughTrack can surface better show alerts.",
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                color = LaughTrackColors.ForegroundMuted,
                modifier = Modifier.widthIn(max = 520.dp),
            )
            FavoriteProgress(favoriteCount)
        }
    }
}

@Composable
private fun FavoriteProgress(favoriteCount: Int) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        repeat(3) { index ->
            val isSelected = index < favoriteCount
            Box(
                Modifier
                    .size(if (isSelected) 10.dp else 9.dp)
                    .clip(CircleShape)
                    .background(if (isSelected) LaughTrackColors.AccentStrong else LaughTrackColors.SurfaceElevated)
                    .border(
                        width = 1.dp,
                        color = if (isSelected) LaughTrackColors.AccentStrong else LaughTrackColors.BorderSubtle,
                        shape = CircleShape,
                    ),
            )
        }
        Text(
            "$favoriteCount/3 selected",
            style = MaterialTheme.typography.labelMedium,
            color = LaughTrackColors.AccentStrong,
        )
    }
}

@Composable
private fun SearchBox(
    query: String,
    isSearchMode: Boolean,
    onQuery: (String) -> Unit,
) {
    OutlinedTextField(
        value = query,
        onValueChange = onQuery,
        placeholder = { Text("Search comedians") },
        singleLine = true,
        leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
        trailingIcon = {
            if (isSearchMode) {
                TextButton(onClick = { onQuery("") }) { Text("Deck") }
            }
        },
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
    )
}

@Composable
private fun SwipeDeck(
    comedians: List<ComedianSearchItem>,
    favorites: Map<String, Boolean>,
    passed: Set<String>,
    canRewind: Boolean,
    layoutSpec: ComedianOnboardingLayoutSpec,
    onFavorite: (String) -> Unit,
    onPass: (String) -> Unit,
    onRewind: () -> Unit,
    onMore: () -> Unit,
) {
    val top = comedians.firstOrNull { favorites[it.uuid] != true && it.uuid !in passed }
    if (top == null) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("No more cards in this deal.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (canRewind) {
                OutlinedButton(onClick = onRewind) { Text("Rewind") }
            }
            OutlinedButton(onClick = onMore) { Text("Deal more") }
        }
        return
    }

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        OnboardingComedianCard(
            comedian = top,
            posterSize = layoutSpec.posterSize,
            cardMaxWidth = layoutSpec.cardMaxWidth,
            onFavorite = { onFavorite(top.uuid) },
            onPass = { onPass(top.uuid) },
        )
        DeckActions(
            canRewind = canRewind,
            spacing = layoutSpec.actionSpacing,
            onRewind = onRewind,
            onPass = { onPass(top.uuid) },
            onFavorite = { onFavorite(top.uuid) },
        )
    }
}

@Composable
private fun OnboardingComedianCard(
    comedian: ComedianSearchItem,
    posterSize: Dp,
    cardMaxWidth: Dp,
    onFavorite: () -> Unit,
    onPass: () -> Unit,
) {
    ComedianCard(
        comedian = comedian,
        posterSize = posterSize,
        onFavorite = onFavorite,
        onPass = onPass,
        modifier = Modifier.widthIn(max = cardMaxWidth).fillMaxWidth(),
    )
}

@Composable
private fun DeckActions(
    canRewind: Boolean,
    spacing: Dp,
    onRewind: () -> Unit,
    onPass: () -> Unit,
    onFavorite: () -> Unit,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(spacing),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularDeckAction(
            contentDescription = "Pass",
            size = 58.dp,
            containerColor = LaughTrackColors.SurfaceElevated,
            contentColor = LaughTrackColors.ForegroundMuted,
            onClick = onPass,
        ) {
            Icon(Icons.Filled.Close, contentDescription = null, modifier = Modifier.size(28.dp))
        }
        CircularDeckAction(
            contentDescription = "Rewind",
            size = 44.dp,
            containerColor = LaughTrackColors.SurfaceElevated,
            contentColor = LaughTrackColors.ForegroundMuted,
            enabled = canRewind,
            onClick = onRewind,
        ) {
            Icon(Icons.Filled.Replay, contentDescription = null, modifier = Modifier.size(21.dp))
        }
        CircularDeckAction(
            contentDescription = "Follow",
            size = 64.dp,
            containerColor = LaughTrackColors.AccentStrong,
            contentColor = LaughTrackColors.Foreground,
            onClick = onFavorite,
        ) {
            Icon(Icons.Filled.Favorite, contentDescription = null, modifier = Modifier.size(28.dp))
        }
    }
}

@Composable
private fun CircularDeckAction(
    contentDescription: String,
    size: Dp,
    containerColor: Color,
    contentColor: Color,
    enabled: Boolean = true,
    onClick: () -> Unit,
    content: @Composable () -> Unit,
) {
    IconButton(
        onClick = onClick,
        enabled = enabled,
        modifier =
            Modifier
                .size(size)
                .alpha(if (enabled) 1f else 0.4f)
                .clip(CircleShape)
                .background(containerColor)
                .border(1.dp, LaughTrackColors.BorderSubtle, CircleShape)
                .semantics { this.contentDescription = contentDescription },
    ) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            androidx.compose.runtime.CompositionLocalProvider(
                androidx.compose.material3.LocalContentColor provides contentColor,
                content = content,
            )
        }
    }
}

@Composable
private fun SearchResults(
    comedians: List<ComedianSearchItem>,
    favorites: Map<String, Boolean>,
    onFavorite: (String) -> Unit,
) {
    if (comedians.isEmpty()) {
        Text("No matches yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        return
    }
    LazyColumn(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(comedians, key = { it.uuid }) { comedian ->
            ComedianRow(
                comedian = comedian,
                isFavorite = favorites[comedian.uuid] == true,
                onFavorite = { onFavorite(comedian.uuid) },
            )
        }
    }
}

@Composable
private fun ComedianCard(
    comedian: ComedianSearchItem,
    onFavorite: () -> Unit,
    onPass: () -> Unit,
    posterSize: Dp,
    modifier: Modifier = Modifier,
) {
    var dragOffset by remember(comedian.uuid) { mutableFloatStateOf(0f) }
    Card(
        modifier =
            modifier
                .offset { IntOffset(dragOffset.roundToInt(), 0) }
                .pointerInput(comedian.uuid) {
                    detectHorizontalDragGestures(
                        onDragEnd = {
                            when {
                                dragOffset > SWIPE_THRESHOLD_PX -> onFavorite()
                                dragOffset < -SWIPE_THRESHOLD_PX -> onPass()
                            }
                            dragOffset = 0f
                        },
                        onHorizontalDrag = { _, dragAmount ->
                            dragOffset += dragAmount
                        },
                    )
                },
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, LaughTrackColors.BorderSubtle),
        colors = CardDefaults.cardColors(containerColor = LaughTrackColors.Surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .background(
                    Brush.radialGradient(
                        colors =
                            listOf(
                                LaughTrackColors.AccentStrong.copy(alpha = 0.22f),
                                LaughTrackColors.Surface,
                            ),
                    ),
                ),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                MarqueePoster(comedian = comedian, posterSize = posterSize)
                Text(
                    comedian.name.uppercase(),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 0.4.sp,
                    textAlign = TextAlign.Center,
                    color = LaughTrackColors.Foreground,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun MarqueePoster(
    comedian: ComedianSearchItem,
    posterSize: Dp,
) {
    val frameSize = posterSize + 12.dp
    Box(Modifier.size(frameSize), contentAlignment = Alignment.Center) {
        RemoteImage(
            url = comedian.imageUrl,
            fallback = RemoteImageFallback.Comedian,
            contentDescription = comedian.name,
            contentScale = ContentScale.Crop,
            modifier = Modifier.size(posterSize).clip(RoundedCornerShape(8.dp)),
        )
        Canvas(Modifier.fillMaxSize()) {
            drawRoundRect(
                color = LaughTrackColors.AccentStrong,
                cornerRadius = CornerRadius(12.dp.toPx()),
                style =
                    Stroke(
                        width = 2.5.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(2.dp.toPx(), 7.dp.toPx())),
                    ),
            )
        }
    }
}

private const val SWIPE_THRESHOLD_PX = 120f

@Composable
private fun ComedianRow(
    comedian: ComedianSearchItem,
    isFavorite: Boolean,
    onFavorite: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onFavorite).padding(8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        RemoteImage(
            url = comedian.imageUrl,
            fallback = RemoteImageFallback.Comedian,
            contentDescription = comedian.name,
            modifier = Modifier.size(56.dp).clip(RoundedCornerShape(10.dp)),
        )
        Column(Modifier.weight(1f)) {
            Text(comedian.name, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${comedian.showCount} shows", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        FavoriteButton(isFavorite = isFavorite, onClick = onFavorite)
    }
}

@Composable
private fun FavoriteButton(
    isFavorite: Boolean,
    onClick: () -> Unit,
) {
    IconButton(onClick = onClick) {
        Icon(
            Icons.Filled.Favorite,
            contentDescription = if (isFavorite) "Remove favorite" else "Add favorite",
            tint = if (isFavorite) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ContinueBar(
    isSaving: Boolean,
    onContinue: () -> Unit,
) {
    Button(
        onClick = onContinue,
        enabled = !isSaving,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp).height(52.dp),
        shape = CircleShape,
        colors =
            ButtonDefaults.buttonColors(
                containerColor = LaughTrackColors.AccentStrong,
                contentColor = Color(0xFF21120C),
            ),
    ) {
        Icon(Icons.Filled.Check, contentDescription = null, modifier = Modifier.size(20.dp))
        Spacer(Modifier.size(8.dp))
        Text(if (isSaving) "Saving..." else "Continue", fontWeight = FontWeight.SemiBold)
    }
}
