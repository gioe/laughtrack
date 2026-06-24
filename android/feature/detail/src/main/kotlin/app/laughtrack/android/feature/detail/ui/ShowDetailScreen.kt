package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.navigation.AppRoute
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.feature.detail.model.ShowDetailUi
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailHero
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.DetailScaffold
import app.laughtrack.android.feature.detail.ui.components.EntityAvatar
import app.laughtrack.android.feature.detail.ui.components.InfoRow
import app.laughtrack.android.feature.detail.ui.components.SectionHeader
import app.laughtrack.android.feature.detail.ui.components.ShowRow
import app.laughtrack.android.feature.detail.util.addEventToCalendar
import app.laughtrack.android.feature.detail.util.formatCountdown
import app.laughtrack.android.feature.detail.util.formatShowDateTime
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.parseShowDateTime
import app.laughtrack.android.feature.detail.util.shareLink
import java.time.ZonedDateTime

@Composable
fun ShowDetailScreen(
    id: Int,
    onBack: () -> Unit,
    onOpenEntity: (AppRoute) -> Unit,
    viewModel: ShowDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val ui = (state as? UiState.Success)?.value

    DetailScaffold(
        title = ui?.detail?.name ?: "Show",
        onBack = onBack,
        onShare = ui?.let { data -> { context.shareLink(data.detail.showPageUrl, data.detail.name) } },
    ) { modifier ->
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = modifier)
            is UiState.Success -> ShowDetailBody(ui!!, modifier, onOpenEntity)
            else -> DetailLoading(modifier)
        }
    }
}

@Composable
private fun ShowDetailBody(
    ui: ShowDetailUi,
    modifier: Modifier,
    onOpenEntity: (AppRoute) -> Unit,
) {
    val context = LocalContext.current
    val detail = ui.detail
    val now = remember { ZonedDateTime.now() }
    Column(
        modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        DetailHero(url = detail.imageUrl, contentDescription = detail.name)

        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            formatCountdown(detail.date, now)?.let { AssistChip(onClick = {}, label = { Text(it) }) }
            Text(detail.name ?: "Show", style = MaterialTheme.typography.headlineSmall)
            InfoRow("When", formatShowDateTime(detail.date))
        }

        ShowVenueSection(ui, onOpenEntity)
        ShowActionsSection(ui)

        detail.description?.takeIf { it.isNotBlank() }?.let { note ->
            Column(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                SectionHeader("About")
                Text(note, style = MaterialTheme.typography.bodyMedium)
            }
        }

        ShowLineupSection(detail.lineup.orEmpty(), onOpenEntity)
        RelatedShowsSection(ui.relatedShows, onOpenEntity)
    }
}

@Composable
private fun ShowVenueSection(ui: ShowDetailUi, onOpenEntity: (AppRoute) -> Unit) {
    val club = ui.detail.club
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        InfoRow("Venue", listOfNotNull(club.name, club.address).joinToString(" · "))
        TextButton(onClick = { onOpenEntity(AppRoute.ClubDetail(club.id)) }) {
            Text("View venue")
        }
    }
}

@Composable
private fun ShowActionsSection(ui: ShowDetailUi) {
    val context = LocalContext.current
    val detail = ui.detail
    val cta = detail.cta
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedButton(
            onClick = {
                val start = parseShowDateTime(detail.date)?.toInstant()?.toEpochMilli() ?: return@OutlinedButton
                context.addEventToCalendar(
                    title = detail.name ?: detail.club.name,
                    startMillis = start,
                    endMillis = null,
                    location = listOfNotNull(detail.club.name, detail.club.address).joinToString(", "),
                    description = "Added from LaughTrack.",
                )
            },
            modifier = Modifier.weight(1f),
        ) {
            Text("Add to calendar")
        }
        Button(
            onClick = { context.openUrl(ui.ticketOutboundUrl) },
            enabled = !cta.isSoldOut && ui.ticketOutboundUrl != null,
            modifier = Modifier.weight(1f),
        ) {
            Text(if (cta.isSoldOut) "Sold out" else cta.label)
        }
    }
}

@Composable
private fun ShowLineupSection(lineup: List<ComedianLineup>, onOpenEntity: (AppRoute) -> Unit) {
    if (lineup.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeader("Lineup", Modifier.padding(horizontal = 16.dp))
        LazyRow(
            contentPadding = PaddingValues(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(lineup) { item ->
                EntityAvatar(
                    name = item.name,
                    imageUrl = item.imageUrl,
                    subtitle = item.role,
                    onClick = { onOpenEntity(AppRoute.ComedianDetail(item.id)) },
                )
            }
        }
    }
}

@Composable
private fun RelatedShowsSection(shows: List<Show>, onOpenEntity: (AppRoute) -> Unit) {
    if (shows.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        SectionHeader("Can't make it?", Modifier.padding(horizontal = 16.dp))
        shows.forEach { show ->
            ShowRow(
                title = show.name ?: show.clubName ?: "Show",
                subtitle = listOfNotNull(show.clubName, show.clubCity).joinToString(" · ").ifBlank { null },
                imageUrl = show.imageUrl,
                onClick = { onOpenEntity(AppRoute.ShowDetail(show.id)) },
            )
        }
    }
}
