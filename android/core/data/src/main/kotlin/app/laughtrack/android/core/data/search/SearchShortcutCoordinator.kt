package app.laughtrack.android.core.data.search

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** The Home search shortcuts, mirroring the iOS SearchRootModel shortcuts. */
enum class SearchShortcut { TONIGHT, THIS_WEEK, NEAR_ME }

/**
 * A one-shot request to seed the Search tab with a shortcut's pre-applied filters.
 * [zip]/[distanceMiles] carry the Home location context so "Near Me" (and the
 * date-window shortcuts) scope to the same area the feed is showing.
 */
data class SearchSeed(
    val shortcut: SearchShortcut,
    val zip: String? = null,
    val distanceMiles: Int? = null,
)

/**
 * Bridges the Home shortcut chips to the Search tab: Home publishes a [SearchSeed]
 * and switches to the Search tab, then Search consumes the seed on its next
 * composition and applies the pre-set filters. Mirrors the shared iOS
 * SearchRootModel that HomeView seeds via `selectShortcut`. Held as a singleton so
 * the Home and Search ViewModels observe the same instance across the tab switch.
 */
@Singleton
class SearchShortcutCoordinator
    @Inject
    constructor() {
        private val _seed = MutableStateFlow<SearchSeed?>(null)
        val seed: StateFlow<SearchSeed?> = _seed.asStateFlow()

        /** Publish a shortcut request; overwrites any unconsumed prior seed. */
        fun request(seed: SearchSeed) {
            _seed.value = seed
        }

        /** Clear the seed once the Search tab has applied it. */
        fun consume() {
            _seed.value = null
        }
    }
