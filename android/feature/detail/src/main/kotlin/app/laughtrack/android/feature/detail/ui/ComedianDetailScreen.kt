package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ComedianHomeLocation
import app.laughtrack.android.core.network.generated.model.PodcastAppearance
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.network.generated.model.UpcomingRun
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.EntityAvatar
import app.laughtrack.android.feature.detail.ui.components.SectionHeader
import app.laughtrack.android.feature.detail.ui.components.ShowRow
import app.laughtrack.android.feature.detail.util.formatHomeCity
import app.laughtrack.android.feature.detail.util.formatHomeClubName
import app.laughtrack.android.feature.detail.util.formatShowDateTime
import app.laughtrack.android.feature.detail.util.openUrl

private val COMEDIAN_TABS = listOf("Shows", "Podcasts", "Related")

@Composable
fun ComedianDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: ComedianDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val favoritesSnapshot by viewModel.favoritesSnapshot.collectAsStateWithLifecycle()
    val ui = (state as? UiState.Success)?.value

    Box(
        Modifier
            .fillMaxSize()
            .background(LaughTrackColors.Canvas),
    ) {
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success ->
                ComedianDetailBody(
                    ui = ui!!,
                    onBack = onBack,
                    isFavorite = favoritesSnapshot.comedianValues[ui.detail.uuid] == true,
                    isFavoritePending = viewModel.isFavoritePending(ui.detail.uuid),
                    onFavorite = { viewModel.toggleFavorite(ui.detail.uuid) },
                    onOpenEntity = onOpenEntity,
                )
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun ComedianDetailBody(
    ui: ComedianDetailUi,
    onBack: () -> Unit,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 28.dp),
    ) {
        ComedianHero(
            ui = ui,
            onBack = onBack,
            isFavorite = isFavorite,
            isFavoritePending = isFavoritePending,
            onFavorite = onFavorite,
            onOpenEntity = onOpenEntity,
        )

        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ComedianTabPicker(selectedTab = selectedTab, onSelectTab = { selectedTab = it })
            when (selectedTab) {
                0 -> ComedianShowsTab(ui, onOpenEntity)
                1 -> ComedianPodcastsTab(ui.detail.podcastAppearances, onOpenEntity)
                else -> ComedianRelatedTab(ui, onOpenEntity)
            }
        }
    }
}

@Composable
private fun ComedianHero(
    ui: ComedianDetailUi,
    onBack: () -> Unit,
    isFavorite: Boolean,
    isFavoritePending: Boolean,
    onFavorite: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(292.dp),
    ) {
        RemoteImage(
            url = ui.detail.imageUrl,
            contentDescription = ui.detail.name,
            modifier = Modifier.fillMaxSize(),
        )
        Box(
            modifier =
                Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            colors =
                                listOf(
                                    LaughTrackColors.Canvas.copy(alpha = 0.05f),
                                    LaughTrackColors.Canvas.copy(alpha = 0.18f),
                                    LaughTrackColors.Canvas.copy(alpha = 0.92f),
                                ),
                        ),
                    ),
        )

        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        ) {
            FloatingHeroButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            FloatingHeroButton(
                onClick = onFavorite,
                selected = isFavorite,
                enabled = !isFavoritePending,
            ) {
                Icon(
                    imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                    contentDescription = if (isFavorite) "Remove favorite" else "Favorite",
                    tint = if (isFavorite) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                )
            }
        }

        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .align(androidx.compose.ui.Alignment.BottomStart)
                    .padding(horizontal = 24.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                ui.detail.name,
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Black),
                color = LaughTrackColors.Foreground,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            ComedianSocialRow(ui.detail.socialData)
            ui.detail.homeLocation?.let { homeLocation ->
                if (HOME_LOCATION_UI_ENABLED) {
                    ComedianHomeLocationRow(homeLocation = homeLocation, onOpenEntity = onOpenEntity)
                }
            }
        }
    }
}

/**
 * Kill-switch for the comedian home-location UI ("Based in / Home club" row).
 * The `homeLocation` data stays wired through the API and model; this only
 * suppresses the user-facing row while the derived home-location data is still
 * unreliable. Flip to `true` to re-expose once the data is trusted. Mirrors the
 * iOS `ComedianHomeLocationPresentation.isUIEnabled` and web
 * `HOME_LOCATION_UI_ENABLED` kill-switches.
 */
private const val HOME_LOCATION_UI_ENABLED = false

@Composable
private fun ComedianHomeLocationRow(
    homeLocation: ComedianHomeLocation,
    onOpenEntity: (AppRoute) -> Unit,
) {
    val cityLabel = formatHomeCity(homeLocation.city, homeLocation.state, homeLocation.country)
    val clubName = formatHomeClubName(homeLocation.clubName)
    // Omit the whole row when no derived home location is present.
    if (cityLabel == null && clubName == null) return

    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        if (cityLabel != null) {
            Text(
                "Based in $cityLabel",
                style = MaterialTheme.typography.bodyMedium,
                color = LaughTrackColors.Foreground,
            )
        }
        if (clubName != null) {
            val clubId = homeLocation.clubId
            if (clubId != null) {
                Text(
                    "Home club: $clubName",
                    style = MaterialTheme.typography.bodyMedium,
                    color = LaughTrackColors.AccentStrong,
                    modifier = Modifier.clickable { onOpenEntity(AppRoute.ClubDetail(clubId)) },
                )
            } else {
                Text(
                    "Home club: $clubName",
                    style = MaterialTheme.typography.bodyMedium,
                    color = LaughTrackColors.Foreground,
                )
            }
        }
    }
}

@Composable
private fun FloatingHeroButton(
    onClick: () -> Unit,
    selected: Boolean = false,
    enabled: Boolean = true,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier =
            Modifier
                .size(36.dp)
                .clip(CircleShape)
                .clickable(enabled = enabled, onClick = onClick),
        color =
            if (selected) {
                LaughTrackColors.SurfaceElevated.copy(alpha = 0.96f)
            } else {
                LaughTrackColors.SurfaceElevated.copy(alpha = if (enabled) 0.9f else 0.64f)
            },
        contentColor = if (enabled) LaughTrackColors.Foreground else LaughTrackColors.ForegroundMuted,
        shape = CircleShape,
    ) {
        Box(contentAlignment = androidx.compose.ui.Alignment.Center) {
            content()
        }
    }
}

@Composable
private fun ComedianSocialRow(social: SocialData) {
    val context = LocalContext.current
    val links = socialLinks(social)
    if (links.isEmpty()) return
    Row(
        Modifier
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        links.forEach { (label, url) ->
            ComedianSocialAction(
                label = label,
                onClick = { context.openUrl(url) },
            )
        }
    }
}

@Composable
private fun ComedianSocialAction(
    label: String,
    onClick: () -> Unit,
) {
    Column(
        modifier =
            Modifier
                .width(62.dp)
                .clickable(onClick = onClick),
        horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Surface(
            modifier = Modifier.size(34.dp),
            color = LaughTrackColors.SurfaceElevated.copy(alpha = 0.92f),
            contentColor = LaughTrackColors.Foreground,
            shape = CircleShape,
        ) {
            Box(contentAlignment = androidx.compose.ui.Alignment.Center) {
                Text(
                    text = label.take(1).uppercase(),
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Black),
                )
            }
        }
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = LaughTrackColors.Foreground,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ComedianTabPicker(
    selectedTab: Int,
    onSelectTab: (Int) -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        COMEDIAN_TABS.forEachIndexed { index, label ->
            val selected = index == selectedTab
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = if (selected) LaughTrackColors.AccentStrong else LaughTrackColors.Surface,
                modifier =
                    Modifier
                        .height(36.dp)
                        .clip(RoundedCornerShape(999.dp))
                        .clickable { onSelectTab(index) }
                        .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp)),
            ) {
                Box(
                    modifier = Modifier.padding(horizontal = 18.dp),
                    contentAlignment = androidx.compose.ui.Alignment.Center,
                ) {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold),
                        color = if (selected) LaughTrackColors.Foreground else LaughTrackColors.ForegroundMuted,
                    )
                }
            }
        }
    }
}

@Composable
private fun ComedianShowsTab(
    ui: ComedianDetailUi,
    onOpenEntity: (AppRoute) -> Unit,
) {
    // The runs/shows are already loaded with the comedian, so filtering and
    // ordering happen client-side — no refetch. (This tab is not geo-scoped, so
    // the old distance/location/date pills never applied here.)
    var clubFilter by remember { mutableStateOf("") }
    var newestFirst by remember { mutableStateOf(true) }

    val filteredRuns =
        ui.upcomingRuns.filter { it.clubName.contains(clubFilter, ignoreCase = true) }
    val filteredPast =
        ui.pastShows
            .filter { show ->
                listOfNotNull(show.clubName, show.name).any { it.contains(clubFilter, ignoreCase = true) }
            }
            .let { shows -> if (newestFirst) shows.sortedByDescending { it.date ?: "" } else shows.sortedBy { it.date ?: "" } }

    Surface(
        modifier =
            Modifier
                .fillMaxWidth()
                .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(16.dp)),
        color = LaughTrackColors.SurfaceElevated,
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "CLUB",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                color = LaughTrackColors.ForegroundMuted,
            )
            ClubFilterField(
                value = clubFilter,
                onValueChange = { clubFilter = it },
            )
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                ShowOrderPill(
                    newestFirst = newestFirst,
                    onSelect = { newestFirst = it },
                )
            }

            if (filteredRuns.isEmpty() && filteredPast.isEmpty()) {
                EmptyShowsPanel(
                    title = "No shows found.",
                    message =
                        if (clubFilter.isBlank()) {
                            "No shows listed for this comedian yet."
                        } else {
                            "No shows match \"$clubFilter\". Try a different club name."
                        },
                )
                return@Column
            }

            if (filteredRuns.isNotEmpty()) {
                SectionHeader("Upcoming")
            }
            filteredRuns.forEach { run ->
                run.shows.forEach { show ->
                    UpcomingRunRow(run = run, showId = show.id, date = show.date, onOpenEntity = onOpenEntity)
                }
            }

            if (filteredPast.isNotEmpty()) {
                SectionHeader("Past shows")
                filteredPast.forEach { show ->
                    ShowRow(
                        title = show.name ?: show.clubName ?: "Show",
                        subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" · ").ifBlank { null },
                        imageUrl = show.imageUrl,
                        onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
                    )
                }
            }
        }
    }
}

/** Real text input that filters the comedian's runs/shows by club name, client-side. */
@Composable
private fun ClubFilterField(
    value: String,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null, tint = LaughTrackColors.ForegroundMuted) },
        placeholder = { Text("Filter by club — Comedy Cellar, The Stand...", maxLines = 1, overflow = TextOverflow.Ellipsis) },
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(999.dp),
    )
}

/** Sort dropdown that reorders the past-shows list by date, client-side. */
@Composable
private fun ShowOrderPill(
    newestFirst: Boolean,
    onSelect: (Boolean) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Surface(
            color = LaughTrackColors.Surface,
            shape = RoundedCornerShape(999.dp),
            modifier =
                Modifier
                    .clip(RoundedCornerShape(999.dp))
                    .clickable { expanded = true }
                    .border(1.dp, LaughTrackColors.BorderSubtle, RoundedCornerShape(999.dp)),
        ) {
            Row(
                modifier = Modifier.padding(start = 12.dp, end = 8.dp, top = 8.dp, bottom = 8.dp),
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
            ) {
                Text(
                    if (newestFirst) "Newest" else "Oldest",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                    color = LaughTrackColors.ForegroundMuted,
                    maxLines = 1,
                )
                Icon(
                    Icons.Filled.ArrowDropDown,
                    contentDescription = null,
                    tint = LaughTrackColors.ForegroundMuted,
                    modifier = Modifier.size(16.dp),
                )
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            listOf(true to "Newest first", false to "Oldest first").forEach { (isNewest, label) ->
                DropdownMenuItem(
                    text = { Text(label) },
                    trailingIcon =
                        if (isNewest == newestFirst) {
                            { Icon(Icons.Filled.Check, contentDescription = null) }
                        } else {
                            null
                        },
                    onClick = {
                        expanded = false
                        onSelect(isNewest)
                    },
                )
            }
        }
    }
}

@Composable
private fun EmptyShowsPanel(
    title: String,
    message: String,
) {
    Surface(
        color = LaughTrackColors.Highlight.copy(alpha = 0.22f),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            Text(message, style = MaterialTheme.typography.bodySmall, color = LaughTrackColors.ForegroundMuted)
        }
    }
}

@Composable
private fun UpcomingRunRow(
    run: UpcomingRun,
    showId: Int,
    date: String,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .clickable { onOpenEntity(AppRoute.ShowDetail(showId)) }
                .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
    ) {
        RemoteImage(
            url = run.clubImageUrl,
            contentDescription = run.clubName,
            modifier =
                Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(10.dp)),
        )
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                run.clubName,
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                formatShowDateTime(date),
                style = MaterialTheme.typography.bodySmall,
                color = LaughTrackColors.ForegroundMuted,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun ComedianPodcastsTab(
    appearances: List<PodcastAppearance>,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (appearances.isEmpty()) {
        EmptyTab("No podcast appearances yet.")
        return
    }
    Column(Modifier.fillMaxWidth()) {
        appearances.forEach { appearance ->
            ShowRow(
                title = appearance.podcast.title,
                subtitle = appearance.episode.title,
                imageUrl = appearance.podcast.imageUrl,
                onClick = { onOpenEntity(AppRoute.PodcastDetail(appearance.podcast.id)) },
            )
        }
    }
}

@Composable
private fun ComedianRelatedTab(
    ui: ComedianDetailUi,
    onOpenEntity: (AppRoute) -> Unit,
) {
    if (ui.coBill.isEmpty()) {
        EmptyTab("No related comedians yet.")
        return
    }
    LazyRow(
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(ui.coBill) { comedian ->
            EntityAvatar(
                name = comedian.name,
                imageUrl = comedian.imageUrl,
                subtitle = comedian.showCount?.let { "$it shows" },
                onClick = { onOpenEntity(AppRoute.ComedianDetail(comedian.id)) },
            )
        }
    }
}

@Composable
private fun EmptyTab(message: String) {
    Row(
        Modifier.fillMaxWidth().padding(24.dp),
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Maps the comedian's social handles to (label, outbound URL) pairs, in display order. */
private fun socialLinks(social: SocialData): List<Pair<String, String>> =
    buildList {
        social.instagramAccount?.takeIf { it.isNotBlank() }?.let {
            add("Instagram" to "https://instagram.com/${it.trimStart('@')}")
        }
        social.tiktokAccount?.takeIf { it.isNotBlank() }?.let {
            add("TikTok" to "https://tiktok.com/@${it.trimStart('@')}")
        }
        social.youtubeAccount?.takeIf { it.isNotBlank() }?.let {
            // youtubeAccount is a bare @handle, not a URL — prefix the host like web
            // (jsonLd.ts) and iOS do, otherwise normalizeUrl yields https://<handle>.
            add("YouTube" to "https://www.youtube.com/@${it.trimStart('@')}")
        }
        social.website?.takeIf { it.isNotBlank() }?.let { add("Website" to normalizeUrl(it)) }
        social.linktree?.takeIf { it.isNotBlank() }?.let { add("Linktree" to normalizeUrl(it)) }
    }

private fun normalizeUrl(raw: String): String =
    if (raw.startsWith("http://") || raw.startsWith("https://")) raw else "https://$raw"
