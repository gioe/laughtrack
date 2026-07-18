package app.laughtrack.android.feature.onboarding

import androidx.compose.ui.unit.dp
import app.laughtrack.android.feature.onboarding.ui.onboardingPortraitHeight
import org.junit.Assert.assertEquals
import org.junit.Test

class ComedianOnboardingLayoutTest {
    @Test
    fun phone_keeps_the_compact_portrait_height() {
        assertEquals(260.dp, onboardingPortraitHeight(372.dp))
    }

    @Test
    fun sevenInchTablet_uses_more_of_the_available_canvas() {
        assertEquals(319.2f, onboardingPortraitHeight(532.dp).value, 0.001f)
    }

    @Test
    fun tenInchTablet_caps_the_portrait_before_it_displaces_actions() {
        assertEquals(360.dp, onboardingPortraitHeight(732.dp))
    }
}
