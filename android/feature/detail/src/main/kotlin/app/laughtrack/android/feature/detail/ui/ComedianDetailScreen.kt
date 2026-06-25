package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.PodcastAppearance
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.feature.detail.model.ComedianDetailUi
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailHero
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.DetailScaffold
import app.laughtrack.android.feature.detail.ui.components.EntityAvatar
import app.laughtrack.android.feature.detail.ui.components.SectionHeader
import app.laughtrack.android.feature.detail.ui.components.ShowRow
import app.laughtrack.android.feature.detail.util.formatShowDateTime
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.shareLink

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
    val context = LocalContext.current
    val ui = (state as? UiState.Success)?.value

    DetailScaffold(
        title = ui?.detail?.name ?: "Comedian",
        onBack = onBack,
        onShare =
            ui?.let { data ->
                { context.shareLink(socialLinks(data.detail.socialData).firstOrNull()?.second, data.detail.name) }
            },
    ) { modifier ->
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = modifier)
            is UiState.Success -> ComedianDetailBody(ui!!, modifier, onOpenEntity)
            else -> DetailLoading(modifier)
        }
    }
}

@Composable
private fun ComedianDetailBody(
    ui: ComedianDetailUi,
    modifier: Modifier,
    onOpenEntity: (AppRoute) -> Unit,
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    Column(
        modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        DetailHero(url = ui.detail.imageUrl, contentDescription = ui.detail.name)
        Text(
            ui.detail.name,
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(horizontal = 16.dp),
        )
        ComedianSocialRow(ui.detail.socialData)

        TabRow(selectedTabIndex = selectedTab) {
            COMEDIAN_TABS.forEachIndexed { index, label ->
                Tab(
                    selected = index == selectedTab,
                    onClick = { selectedTab = index },
                    text = { Text(label) },
                )
            }
        }
        when (selectedTab) {
            0 -> ComedianShowsTab(ui, onOpenEntity)
            1 -> ComedianPodcastsTab(ui.detail.podcastAppearances, onOpenEntity)
            else -> ComedianRelatedTab(ui, onOpenEntity)
        }
    }
}

@Composable
private fun ComedianSocialRow(social: SocialData) {
    val context = LocalContext.current
    val links = socialLinks(social)
    if (links.isEmpty()) return
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        links.forEach { (label, url) ->
            AssistChip(onClick = { context.openUrl(url) }, label = { Text(label) })
        }
    }
}

@Composable
private fun ComedianShowsTab(
    ui: ComedianDetailUi,
    onOpenEntity: (AppRoute) -> Unit,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        if (ui.upcomingRuns.isNotEmpty()) {
            SectionHeader("Upcoming", Modifier.padding(16.dp))
            ui.upcomingRuns.forEach { run ->
                run.shows.forEach { show ->
                    ShowRow(
                        title = run.clubName,
                        subtitle = formatShowDateTime(show.date),
                        imageUrl = run.clubImageUrl,
                        onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
                    )
                }
            }
        }
        if (ui.pastShows.isNotEmpty()) {
            SectionHeader("Past shows", Modifier.padding(16.dp))
            ui.pastShows.forEach { show ->
                ShowRow(
                    title = show.name ?: show.clubName ?: "Show",
                    subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" · ").ifBlank { null },
                    imageUrl = show.imageUrl,
                    onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
                )
            }
        }
        if (ui.upcomingRuns.isEmpty() && ui.pastShows.isEmpty()) {
            EmptyTab("No shows yet.")
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
