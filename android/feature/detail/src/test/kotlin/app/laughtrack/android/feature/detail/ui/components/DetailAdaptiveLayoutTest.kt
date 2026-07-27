package app.laughtrack.android.feature.detail.ui.components

import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Test

class DetailAdaptiveLayoutTest {
    @Test
    fun compactWidthsPreserveThePhoneStack() {
        listOf(440.dp, 599.dp).forEach { width ->
            val spec = detailAdaptiveLayoutSpec(width)

            assertEquals(DetailCatalogLayoutMode.Compact, spec.mode)
            assertEquals(0.dp, spec.outerPadding)
            assertEquals(0.dp, spec.paneGap)
            assertEquals(0.dp, spec.contentTopPadding)
        }
    }

    @Test
    fun sevenInchTabletUsesSafeSplitSizing() {
        val spec = detailAdaptiveLayoutSpec(600.dp)

        assertEquals(DetailCatalogLayoutMode.Expanded, spec.mode)
        assertEquals(8.dp, spec.outerPadding)
        assertEquals(12.dp, spec.paneGap)
        assertEquals(264.dp, spec.heroWidth)
        assertEquals(96.dp, spec.contentTopPadding)
    }

    @Test
    fun tenInchTabletUsesTheWideSplit() {
        val spec = detailAdaptiveLayoutSpec(800.dp)

        assertEquals(DetailCatalogLayoutMode.Expanded, spec.mode)
        assertEquals(32.dp, spec.outerPadding)
        assertEquals(32.dp, spec.paneGap)
        assertEquals(336.dp, spec.heroWidth)
    }

    @Test
    fun expandedContentWidthIsCapped() {
        val spec = detailAdaptiveLayoutSpec(1_600.dp)

        assertEquals(1_200.dp, spec.contentMaxWidth)
        assertEquals(360.dp, spec.heroWidth)
    }
}
