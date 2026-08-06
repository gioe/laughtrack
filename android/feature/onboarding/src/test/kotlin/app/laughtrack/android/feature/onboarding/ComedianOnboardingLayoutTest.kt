package app.laughtrack.android.feature.onboarding

import androidx.compose.ui.unit.dp
import app.laughtrack.android.feature.onboarding.ui.ComedianOnboardingLayoutMode
import app.laughtrack.android.feature.onboarding.ui.OnboardingActionPlacement
import app.laughtrack.android.feature.onboarding.ui.comedianOnboardingLayoutSpec
import org.junit.Assert.assertEquals
import org.junit.Test

class ComedianOnboardingLayoutTest {
    @Test
    fun compactWidthsKeepTheCardAboveItsActions() {
        listOf(440.dp, 599.dp).forEach { width ->
            val spec = comedianOnboardingLayoutSpec(width)

            assertEquals(ComedianOnboardingLayoutMode.Compact, spec.mode)
            assertEquals(16.dp, spec.horizontalPadding)
            assertEquals(14.dp, spec.sectionSpacing)
            assertEquals(260.dp, spec.portraitHeight)
            assertEquals(OnboardingActionPlacement.BelowCard, spec.actionPlacement)
            assertEquals(12.dp, spec.actionSpacing)
        }
    }

    @Test
    fun sevenInchTabletBoundsTheCardAndPlacesActionsBesideIt() {
        val spec = comedianOnboardingLayoutSpec(600.dp)

        assertEquals(ComedianOnboardingLayoutMode.Expanded, spec.mode)
        assertEquals(720.dp, spec.contentMaxWidth)
        assertEquals(16.dp, spec.horizontalPadding)
        assertEquals(18.dp, spec.sectionSpacing)
        assertEquals(360.dp, spec.cardMaxWidth)
        assertEquals(280.dp, spec.portraitHeight)
        assertEquals(OnboardingActionPlacement.BesideCard, spec.actionPlacement)
        assertEquals(16.dp, spec.actionSpacing)
    }

    @Test
    fun tenInchTabletUsesTheWideCardAndActionComposition() {
        val spec = comedianOnboardingLayoutSpec(800.dp)

        assertEquals(ComedianOnboardingLayoutMode.Expanded, spec.mode)
        assertEquals(960.dp, spec.contentMaxWidth)
        assertEquals(32.dp, spec.horizontalPadding)
        assertEquals(24.dp, spec.sectionSpacing)
        assertEquals(400.dp, spec.cardMaxWidth)
        assertEquals(300.dp, spec.portraitHeight)
        assertEquals(OnboardingActionPlacement.BesideCard, spec.actionPlacement)
        assertEquals(18.dp, spec.actionSpacing)
    }

    @Test
    fun expandedCardAndArtworkStayCappedOnWideWindows() {
        val spec = comedianOnboardingLayoutSpec(1_600.dp)

        assertEquals(960.dp, spec.contentMaxWidth)
        assertEquals(400.dp, spec.cardMaxWidth)
        assertEquals(300.dp, spec.portraitHeight)
    }
}
