package app.laughtrack.android.feature.search.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.unit.dp
import app.laughtrack.android.feature.search.model.SearchPivot
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class SearchPivotRowTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun eachSelectedPivotScrollsFullyIntoViewOnNarrowPhone() {
        var selectedPivot by mutableStateOf(SearchPivot.SHOWS)

        composeRule.setContent {
            Box(Modifier.width(220.dp)) {
                SearchPivotRow(
                    selectedPivot = selectedPivot,
                    onSelectPivot = { selectedPivot = it },
                )
            }
        }

        SearchPivot.entries.forEach { pivot ->
            composeRule.runOnIdle { selectedPivot = pivot }
            composeRule.waitForIdle()

            val viewport =
                composeRule.onNodeWithTag(SEARCH_PIVOT_ROW_TEST_TAG).getUnclippedBoundsInRoot()
            val selected =
                composeRule.onNodeWithTag(searchPivotTestTag(pivot)).getUnclippedBoundsInRoot()

            assertTrue("${pivot.name} starts before the pivot viewport", selected.left >= viewport.left)
            assertTrue("${pivot.name} ends after the pivot viewport", selected.right <= viewport.right)
        }
    }
}
