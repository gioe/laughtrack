package app.laughtrack.android.feature.profile

import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Test

class ProfileLayoutTest {
    @Test
    fun compactWidthsUseTheSingleColumnLayout() {
        listOf(440.dp, 599.dp).forEach { width ->
            val spec = profileAdaptiveLayoutSpec(width)

            assertEquals(ProfileLayoutMode.Compact, spec.mode)
            assertEquals(Dp.Infinity, spec.contentMaxWidth)
            assertEquals(24.dp, spec.horizontalPadding)
            assertEquals(18.dp, spec.paneSpacing)
            assertEquals(Dp.Infinity, spec.accountPaneWidth)
            assertEquals(false, spec.centerContentVertically)
        }
    }

    @Test
    fun sevenInchTabletUsesTheSafeExpandedLayout() {
        val spec = profileAdaptiveLayoutSpec(600.dp)

        assertEquals(ProfileLayoutMode.Expanded, spec.mode)
        assertEquals(560.dp, spec.contentMaxWidth)
        assertEquals(8.dp, spec.horizontalPadding)
        assertEquals(12.dp, spec.paneSpacing)
        assertEquals(264.dp, spec.accountPaneWidth)
        assertEquals(true, spec.centerContentVertically)
    }

    @Test
    fun tenInchTabletUsesTheWideExpandedLayout() {
        val spec = profileAdaptiveLayoutSpec(800.dp)

        assertEquals(ProfileLayoutMode.Expanded, spec.mode)
        assertEquals(720.dp, spec.contentMaxWidth)
        assertEquals(32.dp, spec.horizontalPadding)
        assertEquals(32.dp, spec.paneSpacing)
        assertEquals(302.4.dp, spec.accountPaneWidth)
        assertEquals(true, spec.centerContentVertically)
    }

    @Test
    fun expandedContentAndAccountPaneAreCappedOnWideWindows() {
        val spec = profileAdaptiveLayoutSpec(1_600.dp)

        assertEquals(ProfileLayoutMode.Expanded, spec.mode)
        assertEquals(720.dp, spec.contentMaxWidth)
        assertEquals(302.4.dp, spec.accountPaneWidth)
    }
}
