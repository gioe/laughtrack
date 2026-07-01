package app.laughtrack.android.feature.home.data

import android.content.Context
import app.laughtrack.android.core.network.generated.infrastructure.Serializer
import app.laughtrack.android.core.network.generated.model.HomeFeed
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Disk-backed [HomeFeedCache] under the app cache dir. Each (zip, distance) pair
 * is a separate file so switching location doesn't clobber the other's snapshot.
 * A [SCHEMA_VERSION] tag guards the payload: bumping it (after a HomeFeed model
 * change) makes stale entries fail validation and be discarded on the next read,
 * mirroring the iOS PersistentMainPageCache schema-version check.
 */
@Singleton
class PersistentHomeFeedCache
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) : HomeFeedCache {
        private val directory = File(context.cacheDir, "LaughTrackHomeFeedCache")

        override suspend fun get(
            zip: String?,
            distance: Int?,
        ): HomeFeed? =
            withContext(Dispatchers.IO) {
                val file = fileFor(zip, distance)
                if (!file.exists()) return@withContext null

                runCatching {
                    val entry = json.decodeFromString<Entry>(file.readText())
                    if (entry.schemaVersion != SCHEMA_VERSION ||
                        entry.expiresAtMillis <= System.currentTimeMillis()
                    ) {
                        file.delete()
                        null
                    } else {
                        json.decodeFromString<HomeFeed>(entry.feedJson)
                    }
                }.onFailure {
                    // Corrupt/undecodable entry (e.g. model drift without a SCHEMA_VERSION
                    // bump): drop the poison file so it doesn't fail every read until the
                    // next successful set().
                    file.delete()
                }.getOrNull()
            }

        override suspend fun set(
            zip: String?,
            distance: Int?,
            feed: HomeFeed,
        ) {
            withContext(Dispatchers.IO) {
                directory.mkdirs()
                val entry =
                    Entry(
                        schemaVersion = SCHEMA_VERSION,
                        expiresAtMillis = System.currentTimeMillis() + CACHE_TTL_MILLIS,
                        feedJson = json.encodeToString(feed),
                    )
                fileFor(zip, distance).writeText(json.encodeToString(entry))
            }
        }

        private fun fileFor(
            zip: String?,
            distance: Int?,
        ): File {
            val zipPart = zip?.filter(Char::isDigit)?.takeIf { it.isNotBlank() } ?: "default"
            val distancePart = distance?.toString() ?: "default"
            return File(directory, "home-feed-$zipPart-$distancePart.json")
        }

        private companion object {
            const val CACHE_TTL_MILLIS = 60L * 60L * 1000L
            const val SCHEMA_VERSION = "home-feed-v1"
            val json = Serializer.kotlinxSerializationJson
        }

        @Serializable
        private data class Entry(
            val schemaVersion: String,
            val expiresAtMillis: Long,
            val feedJson: String,
        )
    }
