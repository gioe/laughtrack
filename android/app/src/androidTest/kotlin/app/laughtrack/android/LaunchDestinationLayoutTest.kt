package app.laughtrack.android

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

/** Regressions for readiness changes that leave the destination geometry unchanged. */
class LaunchDestinationLayoutTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun consuming_cold_link_releases_identical_bounds_without_remounting_content() {
        val handoff = LaunchHandoff()
        val pending = mutableStateOf(true)
        var mounts = 0
        composeRule.setContent {
            Box(
                Modifier.size(100.dp).launchDestinationLayout(
                    handoff,
                    FirstEntryRootSurface.AppShell,
                    pending.value,
                ),
            ) {
                DisposableEffect(Unit) {
                    mounts++
                    onDispose { }
                }
            }
        }
        composeRule.runOnIdle {
            assertTrue(handoff.keepSplashVisible)
            pending.value = false
        }
        composeRule.runOnIdle {
            assertFalse(handoff.keepSplashVisible)
            assertEquals(1, mounts)
        }
    }

    @Test
    fun resolved_root_releases_even_when_loading_and_destination_have_identical_bounds() {
        val handoff = LaunchHandoff()
        val surface = mutableStateOf(FirstEntryRootSurface.Loading)
        composeRule.setContent {
            Box(Modifier.size(100.dp).launchDestinationLayout(handoff, surface.value, false))
        }
        composeRule.runOnIdle {
            assertTrue(handoff.keepSplashVisible)
            surface.value = FirstEntryRootSurface.Recovery
        }
        composeRule.runOnIdle { assertFalse(handoff.keepSplashVisible) }
    }
}
