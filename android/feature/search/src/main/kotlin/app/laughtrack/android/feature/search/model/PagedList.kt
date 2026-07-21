package app.laughtrack.android.feature.search.model

/**
 * Immutable paginated-list state with a pure reducer, so pagination semantics
 * (append the next page, replace on a fresh query, derive hasMore from the server
 * total) are unit-testable without Android. The public search API paginates by
 * zero-based `page` + `size` and returns a `total`; a new query resets to an
 * empty list and loads page 0.
 */
data class PagedList<T>(
    val items: List<T> = emptyList(),
    val page: Int = -1,
    val total: Int = 0,
    val isLoading: Boolean = false,
    val error: String? = null,
) {
    /** More pages exist iff fewer items are loaded than the server's reported total. */
    val hasMore: Boolean get() = items.size < total

    val nextPage: Int get() = page + 1

    fun loading(): PagedList<T> = copy(isLoading = true, error = null)

    /**
     * Fold a freshly-loaded page into the state. Page 0 replaces the list
     * — that is how a query/filter change resets pagination — while later pages
     * append.
     *
     * [dedupKey] drops rows whose key was already loaded (first occurrence wins,
     * so existing rows keep their position). Required when the search lazy grid
     * keys rows by that same identity: offset pagination can return
     * an entity on two pages when the result set shifts mid-scroll, and a
     * duplicate key crashes the list instead of just re-binding it.
     */
    fun appendPage(
        loadedPage: Int,
        pageItems: List<T>,
        total: Int,
        dedupKey: ((T) -> Any)? = null,
    ): PagedList<T> {
        val merged = if (loadedPage == 0) pageItems else items + pageItems
        return copy(
            items = if (dedupKey != null) merged.distinctBy(dedupKey) else merged,
            page = loadedPage,
            total = total,
            isLoading = false,
            error = null,
        )
    }

    fun failed(message: String): PagedList<T> = copy(isLoading = false, error = message)
}
