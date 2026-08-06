package app.laughtrack.android.feature.onboarding

import androidx.compose.ui.unit.dp
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingLayoutMode
import app.laughtrack.android.feature.onboarding.ui.comedianOnboardingLayoutSpec
import org.junit.Assert.assertEquals
import org.junit.Test

class ComedianOnboardingLayoutTest {
    @Test
    fun compactWidthsUseThePhonePosterComposition() {
        listOf(440.dp, 599.dp).forEach { width ->
            val spec = comedianOnboardingLayoutSpec(width)

            assertEquals(ComedianOnboardingLayoutMode.Compact, spec.mode)
            assertEquals(16.dp, spec.horizontalPadding)
            assertEquals(14.dp, spec.sectionSpacing)
            assertEquals(220.dp, spec.posterSize)
            assertEquals(22.dp, spec.actionSpacing)
        }
    }

    @Test
    fun sevenInchTabletKeepsTheCenteredPosterDeck() {
        val spec = comedianOnboardingLayoutSpec(600.dp)

        assertEquals(ComedianOnboardingLayoutMode.Expanded, spec.mode)
        assertEquals(560.dp, spec.contentMaxWidth)
        assertEquals(24.dp, spec.horizontalPadding)
        assertEquals(18.dp, spec.sectionSpacing)
        assertEquals(480.dp, spec.cardMaxWidth)
        assertEquals(240.dp, spec.posterSize)
        assertEquals(24.dp, spec.actionSpacing)
    }

    @Test
    fun tenInchTabletUsesTheWideCenteredPosterComposition() {
        val spec = comedianOnboardingLayoutSpec(800.dp)

        assertEquals(ComedianOnboardingLayoutMode.Expanded, spec.mode)
        assertEquals(620.dp, spec.contentMaxWidth)
        assertEquals(32.dp, spec.horizontalPadding)
        assertEquals(20.dp, spec.sectionSpacing)
        assertEquals(520.dp, spec.cardMaxWidth)
        assertEquals(260.dp, spec.posterSize)
        assertEquals(28.dp, spec.actionSpacing)
    }

    @Test
    fun expandedCardAndArtworkStayCappedOnWideWindows() {
        val spec = comedianOnboardingLayoutSpec(1_600.dp)

        assertEquals(620.dp, spec.contentMaxWidth)
        assertEquals(520.dp, spec.cardMaxWidth)
        assertEquals(260.dp, spec.posterSize)
    }
}
