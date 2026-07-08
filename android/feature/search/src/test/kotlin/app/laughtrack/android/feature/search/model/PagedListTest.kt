package app.laughtrack.android.feature.search.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Locks the pagination reducer: page-1 replaces (query reset), later pages append,
 *  hasMore derives from total, and failure clears loading. */
class PagedListTest {
    @Test
    fun first_page_replaces_items_and_records_total() {
        val state = PagedList<String>().loading().appendPage(1, listOf("a", "b"), total = 5)
        assertEquals(listOf("a", "b"), state.items)
        assertEquals(1, state.page)
        assertEquals(5, state.total)
        assertTrue(state.hasMore)
        assertFalse(state.isLoading)
        assertEquals(2, state.nextPage)
    }

    @Test
    fun later_pages_append() {
        val state =
            PagedList<String>()
                .appendPage(1, listOf("a", "b"), total = 5)
                .appendPage(2, listOf("c", "d"), total = 5)
        assertEquals(listOf("a", "b", "c", "d"), state.items)
        assertEquals(2, state.page)
        assertTrue(state.hasMore)
    }

    @Test
    fun has_more_is_false_once_all_items_loaded() {
        val state = PagedList<String>().appendPage(1, listOf("a", "b"), total = 2)
        assertFalse(state.hasMore)
    }

    @Test
    fun reloading_page_one_resets_accumulated_pages() {
        val loaded =
            PagedList<String>()
                .appendPage(1, listOf("a", "b"), total = 5)
                .appendPage(2, listOf("c"), total = 5)
        // A query/filter change re-fetches page 1, which must replace, not append.
        val reset = loaded.appendPage(1, listOf("x"), total = 1)
        assertEquals(listOf("x"), reset.items)
        assertEquals(1, reset.page)
        assertFalse(reset.hasMore)
    }

    @Test
    fun failed_sets_error_and_clears_loading() {
        val state = PagedList<String>().loading().failed("boom")
        assertEquals("boom", state.error)
        assertFalse(state.isLoading)
    }

    @Test
    fun dedup_key_drops_rows_already_loaded_keeping_first_occurrence() {
        // Offset pagination can re-serve an entity on a later page when the
        // result set shifts mid-scroll; the route-keyed LazyColumn would crash
        // on the duplicate key without this.
        val state =
            PagedList<String>()
                .appendPage(1, listOf("a", "b"), total = 5, dedupKey = { it })
                .appendPage(2, listOf("b", "c"), total = 5, dedupKey = { it })
        assertEquals(listOf("a", "b", "c"), state.items)
    }

    @Test
    fun dedup_key_applies_within_a_single_page() {
        val state = PagedList<String>().appendPage(1, listOf("a", "a", "b"), total = 3, dedupKey = { it })
        assertEquals(listOf("a", "b"), state.items)
    }

    @Test
    fun append_without_dedup_key_keeps_duplicates() {
        val state =
            PagedList<String>()
                .appendPage(1, listOf("a", "b"), total = 4)
                .appendPage(2, listOf("b", "c"), total = 4)
        assertEquals(listOf("a", "b", "b", "c"), state.items)
    }
}
