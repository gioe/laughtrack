package app.laughtrack.android.feature.home.data

import app.laughtrack.android.core.network.generated.model.HomeFeed

/**
 * Persists the composite home feed so the Discover tab re-renders instantly from
 * disk on relaunch, keyed by the (zip, distance) it was fetched for. Mirrors the
 * iOS PersistentMainPageCache: entries are schema-versioned so a model change
 * discards stale payloads rather than deserializing them incorrectly.
 */
interface HomeFeedCache {
    suspend fun get(
        zip: String?,
        distance: Int?,
    ): HomeFeed?

    suspend fun set(
        zip: String?,
        distance: Int?,
        feed: HomeFeed,
    )
}
