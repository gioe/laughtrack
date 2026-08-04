package app.laughtrack.android.feature.search.model

/**
 * A single sort choice: the server [apiValue] sent as the `sort` query param and
 * the human [label] shown in the sort dropdown. Mirrors the raw values in iOS
 * SearchOptions.swift (and web's getSortOptionsForEntityType) so all three
 * clients sort identically.
 */
data class SortOption(
    val apiValue: String,
    val label: String,
)

/** Distance radius choices (miles) for geo-scoped search pivots. */
val DISTANCE_OPTIONS: List<Int> = listOf(10, 25, 50, 100)

/** Default radius when a ZIP is set but no distance is chosen. */
const val DEFAULT_DISTANCE_MILES: Int = 25

/** Stable show-format facets understood by the shows search endpoint. */
enum class ShowFormatOption(
    val slug: String,
    val label: String,
) {
    STAND_UP("standup", "Stand-up"),
    IMPROV("improv", "Improv"),
    OPEN_MIC("open_mic", "Open mic"),
}

/** Direct maximum-price choices for show exploration. */
enum class ShowMaximumPriceOption(
    val apiValue: Int?,
    val label: String,
) {
    ANY(null, "Any price"),
    TWENTY(20, "Up to $20"),
    FORTY(40, "Up to $40"),
    SIXTY(60, "Up to $60"),
    HUNDRED(100, "Up to $100"),
    ;

    companion object {
        fun fromApiValue(value: Int?): ShowMaximumPriceOption = entries.firstOrNull { it.apiValue == value } ?: ANY
    }
}

/** The two first-class ways to browse show results. */
enum class ShowResultsPresentation(
    val label: String,
) {
    AGENDA("Agenda"),
    CALENDAR("Calendar"),
}

/** Direct date shortcuts shown ahead of the full date-range picker. */
enum class ShowDateShortcut(
    val label: String,
) {
    TONIGHT("Tonight"),
    THIS_WEEKEND("This Weekend"),
}

/**
 * Per-pivot sort vocabularies and their defaults. The first entry in each list is
 * the server's implicit default sort for that entity type, so it doubles as the
 * initial selection. Kept byte-for-byte aligned with iOS SearchOptions.swift.
 */
object SearchSort {
    private val SHOWS =
        listOf(
            SortOption("date_asc", "Earliest"),
            SortOption("date_desc", "Latest"),
            SortOption("price_asc", "Low price"),
            SortOption("price_desc", "High price"),
        )

    private val COMEDIANS =
        listOf(
            SortOption("popularity_desc", "Most popular"),
            SortOption("popularity_asc", "Least popular"),
            SortOption("name_asc", "A-Z"),
            SortOption("name_desc", "Z-A"),
        )

    // Clubs lead with "Most active" (total_shows_desc) because popularity data is
    // sparse for venues — matches iOS ClubSortOption / web.
    private val CLUBS =
        listOf(
            SortOption("total_shows_desc", "Most active"),
            SortOption("total_shows_asc", "Least active"),
            SortOption("popularity_desc", "Most popular"),
            SortOption("popularity_asc", "Least popular"),
            SortOption("name_asc", "A-Z"),
            SortOption("name_desc", "Z-A"),
        )

    // Podcasts sort by episode count because "popularity" is meaningless for
    // episodic content — matches iOS PodcastSortOption / web ("Most Episodes").
    private val PODCASTS =
        listOf(
            SortOption("show_count_desc", "Most episodes"),
            SortOption("show_count_asc", "Fewest episodes"),
            SortOption("name_asc", "A-Z"),
            SortOption("name_desc", "Z-A"),
        )

    fun optionsFor(pivot: SearchPivot): List<SortOption> =
        when (pivot) {
            SearchPivot.SHOWS -> SHOWS
            SearchPivot.COMEDIANS -> COMEDIANS
            SearchPivot.CLUBS -> CLUBS
            SearchPivot.PODCASTS -> PODCASTS
        }

    /** The default (leading) sort key for a pivot — the server's implicit default. */
    fun defaultFor(pivot: SearchPivot): String = optionsFor(pivot).first().apiValue

    /** Display label for the currently-selected [apiValue], falling back to the pivot default. */
    fun labelFor(
        pivot: SearchPivot,
        apiValue: String?,
    ): String {
        val options = optionsFor(pivot)
        return options.firstOrNull { it.apiValue == apiValue }?.label ?: options.first().label
    }
}
