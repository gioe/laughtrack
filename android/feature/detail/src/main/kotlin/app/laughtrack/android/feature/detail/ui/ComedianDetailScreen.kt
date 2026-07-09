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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ComedianHomeLocation
import app.laughtrack.android.core.network.generated.model.PodcastAppearance
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.network.generated.model.UpcomingRun
import app.laughtrack.android.core.ui.UiState
import app.laughtrack.android.core.ui.components.RemoteImage
import app.laughtrack.android.core.ui.components.ticketStubDateParts
import app.laughtrack.android.core.ui.theme.LaughTrackColors
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.EntityAvatar
import app.laughtrack.android.feature.detail.ui.components.SectionHeader
import app.laughtrack.android.feature.detail.ui.components.ShowRow
import app.laughtrack.android.feature.detail.ui.components.TicketShowRow
import app.laughtrack.android.feature.detail.util.formatHomeCity
import app.laughtrack.android.feature.detail.util.formatHomeClubName
import app.laughtrack.android.feature.detail.util.formatTicketPriceLabel
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.showRowTitleSubtitle

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

    Box(
        Modifier
            .fillMaxSize()
            .background(LaughTrackColors.Canvas),
    ) {
        when (val s = state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = Modifier.fillMaxSize())
            is UiState.Success -> {
                val ui = s.value
                ComedianDetailBody(
                    ui = ui,
                    onBack = onBack,
                    isFavorite = favoritesSnapshot.comedianValues[ui.detail.uuid] == true,
                    isFavoritePending = viewModel.isFavoritePending(ui.detail.uuid),
                    onFavorite = { viewModel.toggleFavorite(ui.detail.uuid) },
                    onOpenEntity = onOpenEntity,
                )
            }
            else -> DetailLoading(Modifier.fillMaxSize())
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
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
    Scaffold(
        containerColor = LaughTrackColors.Canvas,
        topBar = {
            TopAppBar(
                title = {},
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = onFavorite, enabled = !isFavoritePending) {
                        Icon(
                            imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                            contentDescription = if (isFavorite) "Remove favorite" else "Favorite",
                            tint = if (isFavorite) LaughTrackColors.AccentStrong else LaughTrackColors.Foreground,
                        )
                    }
                },
                colors =
                    TopAppBarDefaults.topAppBarColors(
                        containerColor = LaughTrackColors.Canvas,
                        navigationIconContentColor = LaughTrackColors.Foreground,
                        actionIconContentColor = LaughTrackColors.Foreground,
                        titleContentColor = LaughTrackColors.Foreground,
                    ),
            )
        },
    ) { innerPadding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(bottom = 28.dp),
        ) {
            ComedianIdentityBlock(ui = ui, onOpenEntity = onOpenEntity)

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
}

/**
 * Centered, polaroid-framed identity block mirroring the iOS 07_ComedianDetail
 * treatment (see MarqueeHero `.framedComedian` / ClubWallHeadshotFrame): a warm
 * cream→tan matte holding the square portrait plus a serif name caption, tilted a
 * hair, above the name heading and the social row. Replaces the old full-bleed hero.
 */
@Composable
private fun ComedianIdentityBlock(
    ui: ComedianDetailUi,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        ComedianPolaroid(imageUrl = ui.detail.imageUrl, name = ui.detail.name)
        Text(
            ui.detail.name,
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Black),
            color = LaughTrackColors.Foreground,
            textAlign = TextAlign.Center,
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

/**
 * The polaroid frame itself, mirroring iOS ClubWallHeadshotFrame: cream→tan matte
 * gradient, square photo with a hairline dark border, a serif uppercase name caption
 * on a translucent white strip, a thick dark outer edge, a slight tilt, and a soft
 * drop shadow.
 */
@Composable
private fun ComedianPolaroid(
    imageUrl: String?,
    name: String,
) {
    val frameShape = RoundedCornerShape(8.dp)
    Column(
        Modifier
            .rotate(-0.4f)
            .shadow(elevation = 12.dp, shape = frameShape, clip = false)
            .clip(frameShape)
            .background(
                Brush.linearGradient(
                    colors =
                        listOf(
                            LaughTrackColors.Foreground.copy(alpha = 0.94f),
                            Color(0xFFD1C2A8),
                        ),
                ),
            )
            .border(3.dp, Color.Black.copy(alpha = 0.72f), frameShape)
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // Portrait + caption are decorative: the name is announced once via the
        // headline below (mirrors iOS marking the polaroid caption accessibilityHidden).
        RemoteImage(
            url = imageUrl,
            contentDescription = null,
            modifier =
                Modifier
                    .size(200.dp)
                    .clip(RectangleShape)
                    .border(1.dp, Color.Black.copy(alpha = 0.5f), RectangleShape),
        )
        Text(
            name.uppercase(),
            style =
                MaterialTheme.typography.labelMedium.copy(
                    fontFamily = FontFamily.Serif,
                    fontWeight = FontWeight.SemiBold,
                    letterSpacing = 0.4.sp,
                ),
            color = Color.Black.copy(alpha = 0.74f),
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier =
                Modifier
                    .width(200.dp)
                    .background(Color.White.copy(alpha = 0.30f))
                    .padding(vertical = 2.dp)
                    .clearAndSetSemantics {},
        )
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
            .let { shows ->
                if (newestFirst) shows.sortedByDescending { it.date ?: "" } else shows.sortedBy { it.date ?: "" }
            }

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
                    UpcomingRunRow(run = run, show = show, onOpenEntity = onOpenEntity)
                }
            }

            if (filteredPast.isNotEmpty()) {
                SectionHeader("Past shows")
                filteredPast.forEach { show ->
                    val (title, subtitle) = showRowTitleSubtitle(show.name, show.clubName, show.clubCity)
                    TicketShowRow(
                        title = title,
                        subtitle = subtitle,
                        imageUrl = show.imageUrl,
                        dateParts = ticketStubDateParts(isoDateTime = show.date, timezone = show.timezone),
                        priceLabel = null,
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
        placeholder = {
            Text("Filter by club — Comedy Cellar, The Stand...", maxLines = 1, overflow = TextOverflow.Ellipsis)
        },
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
    show: Show,
    onOpenEntity: (AppRoute) -> Unit,
) {
    TicketShowRow(
        title = run.clubName,
        subtitle = show.name?.takeUnless { it.equals(run.clubName, ignoreCase = true) },
        imageUrl = run.clubImageUrl,
        dateParts = ticketStubDateParts(isoDateTime = show.date, timezone = show.timezone),
        priceLabel = formatTicketPriceLabel(show.tickets, show.soldOut),
        onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
    )
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
        items(ui.coBill, key = { it.id }) { comedian ->
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
