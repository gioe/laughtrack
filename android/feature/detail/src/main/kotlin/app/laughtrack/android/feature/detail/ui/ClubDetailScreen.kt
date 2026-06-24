package app.laughtrack.android.feature.detail.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.laughtrack.android.core.data.UiState
import app.laughtrack.android.core.network.generated.model.ClubDetail
import app.laughtrack.android.feature.detail.ui.components.DetailError
import app.laughtrack.android.feature.detail.ui.components.DetailHero
import app.laughtrack.android.feature.detail.ui.components.DetailLoading
import app.laughtrack.android.feature.detail.ui.components.DetailScaffold
import app.laughtrack.android.feature.detail.ui.components.InfoRow
import app.laughtrack.android.feature.detail.util.dialPhone
import app.laughtrack.android.feature.detail.util.openMap
import app.laughtrack.android.feature.detail.util.openUrl
import app.laughtrack.android.feature.detail.util.shareLink

@Composable
fun ClubDetailScreen(
    id: Int,
    onBack: () -> Unit,
    viewModel: ClubDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val club = (state as? UiState.Success)?.value

    DetailScaffold(
        title = club?.name ?: "Venue",
        onBack = onBack,
        onShare = club?.let { data -> { context.shareLink(data.website, data.name) } },
    ) { modifier ->
        when (state) {
            is UiState.Failure -> DetailError(onRetry = viewModel::retry, modifier = modifier)
            is UiState.Success -> ClubDetailBody(club!!, modifier)
            else -> DetailLoading(modifier)
        }
    }
}

@Composable
private fun ClubDetailBody(club: ClubDetail, modifier: Modifier) {
    val context = LocalContext.current
    Column(
        modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        DetailHero(url = club.heroImageUrl.ifBlank { club.imageUrl }, contentDescription = club.name)
        Text(
            club.name,
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(horizontal = 16.dp),
        )
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            InfoRow("Address", club.address)
            club.phoneNumber?.takeIf { it.isNotBlank() }?.let { InfoRow("Phone", it) }
        }
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedButton(
                onClick = { context.openUrl(club.website) },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Visit website")
            }
            OutlinedButton(
                onClick = { context.openMap(club.address) },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Open in maps")
            }
            club.phoneNumber?.takeIf { it.isNotBlank() }?.let { phone ->
                OutlinedButton(
                    onClick = { context.dialPhone(phone) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Call venue")
                }
            }
        }
    }
}
