package app.laughtrack.android.feature.search.ui

import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Test

class SearchAdaptiveLayoutTest {
    @Test
    fun phone_widths_keep_the_compact_single_column_layout() {
        assertEquals(SearchLayoutMode.Compact, searchAdaptiveLayoutSpec(440.dp).mode)
        assertEquals(1, searchAdaptiveLayoutSpec(440.dp).resultColumns)
        assertEquals(SearchLayoutMode.Compact, searchAdaptiveLayoutSpec(599.dp).mode)
    }

    @Test
    fun tablet_widths_use_two_result_columns() {
        assertEquals(SearchLayoutMode.Expanded, searchAdaptiveLayoutSpec(600.dp).mode)
        assertEquals(2, searchAdaptiveLayoutSpec(600.dp).resultColumns)
        assertEquals(SearchLayoutMode.Expanded, searchAdaptiveLayoutSpec(800.dp).mode)
        assertEquals(2, searchAdaptiveLayoutSpec(800.dp).resultColumns)
    }

    @Test
    fun expanded_content_is_capped_for_wide_windows() {
        assertEquals(1_200.dp, searchAdaptiveLayoutSpec(600.dp).contentMaxWidth)
        assertEquals(1_200.dp, searchAdaptiveLayoutSpec(1_600.dp).contentMaxWidth)
    }
}
