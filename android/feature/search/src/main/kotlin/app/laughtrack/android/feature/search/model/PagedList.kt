package app.laughtrack.android.feature.search.model

/**
 * Immutable paginated-list state with a pure reducer, so pagination semantics
 * (append the next page, replace on a fresh query, derive hasMore from the server
 * total) are unit-testable without Android. The server paginates by 1-based
 * `page` + `size` and returns a `total`; a new query resets to an empty list and
 * loads page 1.
 */
data class PagedList<T>(
    val items: List<T> = emptyList(),
    val page: Int = 0,
    val total: Int = 0,
    val isLoading: Boolean = false,
    val error: String? = null,
) {
    /** More pages exist iff fewer items are loaded than the server's reported total. */
    val hasMore: Boolean get() = items.size < total

    val nextPage: Int get() = page + 1

    fun loading(): PagedList<T> = copy(isLoading = true, error = null)

    /**
     * Fold a freshly-loaded page into the state. Page 1 (or 0) replaces the list
     * — that is how a query/filter change resets pagination — while later pages
     * append.
     */
    fun appendPage(
        loadedPage: Int,
        pageItems: List<T>,
        total: Int,
    ): PagedList<T> =
        copy(
            items = if (loadedPage <= 1) pageItems else items + pageItems,
            page = loadedPage,
            total = total,
            isLoading = false,
            error = null,
        )

    fun failed(message: String): PagedList<T> = copy(isLoading = false, error = message)
}
