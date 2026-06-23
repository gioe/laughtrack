package app.laughtrack.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.HomeScreen
import dagger.hilt.android.AndroidEntryPoint

/**
 * Single-Activity host. Real tab/navigation wiring lands in the app-shell task
 * (TASK-3258); this scaffold renders the placeholder Home surface so the project
 * compiles and runs end-to-end.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { LaughTrackApp() }
    }
}

@Composable
private fun LaughTrackApp() {
    LaughTrackTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Scaffold { innerPadding ->
                HomeScreen(modifier = Modifier.padding(innerPadding))
            }
        }
    }
}
