package app.laughtrack.android.screenshots

import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.profile.ProfileAccount
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.data.savedshows.SavedShowsCollection
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianLineup
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.NotificationComedian
import app.laughtrack.android.core.network.generated.model.NotificationItem
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import app.laughtrack.android.core.network.generated.model.NotificationShow
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.feature.profile.ProfileUiState
import java.time.ZonedDateTime

/**
 * Credentials-free, immutable content for authenticated screenshot captures.
 *
 * The persona deliberately contains no remote image URLs and never enters the
 * authentication or networking layers. It is passed explicitly by screenshot
 * tests; production navigation continues to use the Hilt-backed screen models.
 * Empty artwork values intentionally exercise the same branded fallback policy
 * as the iOS persona.
 */
object AuthenticatedScreenshotPersona {
    const val COMEDIAN_UUID = "00000000-0000-4000-8000-000000000101"
    const val SECOND_COMEDIAN_UUID = "00000000-0000-4000-8000-000000000102"
    const val SHOW_ID = 910_101
    const val SECOND_SHOW_ID = 910_102
    const val UPCOMING_SAVED_SHOW_ID = 910_103
    const val PAST_SAVED_SHOW_ID = 910_104

    val profileUiState =
        ProfileUiState(
            signedIn = true,
            account =
                ProfileAccount(
                    displayName = "Jordan Rivera",
                    email = "jordan.rivera@example.invalid",
                    avatarUrl = null,
                ),
            preferences =
                ProfilePreferences(
                    zipCode = "10012",
                    nearbyDistanceMiles = 25,
                    emailShowNotifications = true,
                    pushShowNotifications = true,
                ),
            zipCodeDraft = "10012",
            selectedDistanceMiles = 25,
            isLoading = false,
        )

    val favoritesSnapshot =
        FavoritesSnapshot(
            comedians =
                listOf(
                    ComedianSearchItem(
                        id = 910_001,
                        uuid = COMEDIAN_UUID,
                        name = "Taylor Tomlinson",
                        imageUrl = "",
                        socialData = SocialData(id = 910_001),
                        showCount = 2,
                        isFavorite = true,
                    ),
                    ComedianSearchItem(
                        id = 910_002,
                        uuid = SECOND_COMEDIAN_UUID,
                        name = "Sam Jay",
                        imageUrl = "",
                        socialData = SocialData(id = 910_002),
                        showCount = 1,
                        isFavorite = true,
                    ),
                ),
            shows =
                listOf(
                    Show(
                        id = SHOW_ID,
                        clubId = 910_201,
                        date = "2026-07-18T20:00:00-04:00",
                        imageUrl = "",
                        clubName = "The Comedy Cellar",
                        clubCity = "New York",
                        clubState = "NY",
                        name = "Taylor Tomlinson Live",
                        lineup =
                            listOf(
                                ComedianLineup(
                                    name = "Taylor Tomlinson",
                                    imageUrl = "",
                                    uuid = COMEDIAN_UUID,
                                    id = 910_001,
                                    isFavorite = true,
                                ),
                            ),
                        timezone = "America/New_York",
                    ),
                    Show(
                        id = SECOND_SHOW_ID,
                        clubId = 910_202,
                        date = "2026-07-19T19:30:00-04:00",
                        imageUrl = "",
                        clubName = "The Bell House",
                        clubCity = "Brooklyn",
                        clubState = "NY",
                        name = "Sam Jay Live",
                        lineup =
                            listOf(
                                ComedianLineup(
                                    name = "Sam Jay",
                                    imageUrl = "",
                                    uuid = SECOND_COMEDIAN_UUID,
                                    id = 910_002,
                                    isFavorite = true,
                                ),
                            ),
                        timezone = "America/New_York",
                    ),
                ),
            clubs =
                listOf(
                    FavoriteClubItem(
                        id = 910_201,
                        name = "The Comedy Cellar",
                        imageUrl = "",
                        isFavorite = true,
                    ),
                ),
            podcasts =
                listOf(
                    FavoritePodcastItem(
                        id = 910_301,
                        title = "Good One: A Podcast About Jokes",
                        episodeCount = 248,
                        isFavorite = true,
                        authorName = "Vulture",
                        imageUrl = null,
                    ),
                ),
            comedianValues = mapOf(COMEDIAN_UUID to true, SECOND_COMEDIAN_UUID to true),
            clubValues = mapOf(910_201 to true),
            podcastValues = mapOf(910_301 to true),
        )

    val savedShowsSnapshot =
        SavedShowsSnapshot(
            values =
                mapOf(
                    UPCOMING_SAVED_SHOW_ID to true,
                    PAST_SAVED_SHOW_ID to true,
                ),
            upcoming =
                SavedShowsCollection(
                    shows =
                        listOf(
                            Show(
                                id = UPCOMING_SAVED_SHOW_ID,
                                clubId = 910_203,
                                date = "2026-07-30T20:00:00-04:00",
                                imageUrl = "",
                                clubName = "Gotham Comedy Club",
                                clubCity = "New York",
                                clubState = "NY",
                                name = "Thursday Night Stand-Up",
                                timezone = "America/New_York",
                            ),
                        ),
                    page = 1,
                    total = 1,
                    totalPages = 1,
                ),
            past =
                SavedShowsCollection(
                    shows =
                        listOf(
                            Show(
                                id = PAST_SAVED_SHOW_ID,
                                clubId = 910_204,
                                date = "2026-07-12T19:30:00-04:00",
                                imageUrl = "",
                                clubName = "Union Hall",
                                clubCity = "Brooklyn",
                                clubState = "NY",
                                name = "Sunday Comedy Showcase",
                                timezone = "America/New_York",
                            ),
                        ),
                    page = 1,
                    total = 1,
                    totalPages = 1,
                ),
        )

    val notificationListResponseData =
        NotificationListResponseData(
            items =
                listOf(
                    NotificationItem(
                        id = "screenshot-notification-001",
                        title = "Taylor Tomlinson has a show near you",
                        body = "The Comedy Cellar on Saturday at 8:00 PM",
                        comedianName = "Taylor Tomlinson",
                        comedianImageUrl = "",
                        comedians =
                            listOf(
                                NotificationComedian(
                                    comedianId = COMEDIAN_UUID,
                                    comedianName = "Taylor Tomlinson",
                                    comedianImageUrl = "",
                                ),
                            ),
                        shows =
                            listOf(
                                NotificationShow(
                                    showId = SHOW_ID,
                                    subtitle = "The Comedy Cellar on Saturday at 8:00 PM",
                                    showPageUrl = null,
                                    showDate = "2026-07-18T20:00:00-04:00",
                                    clubName = "The Comedy Cellar",
                                    city = "New York",
                                    state = "NY",
                                ),
                            ),
                        channels = listOf("push", "email"),
                        sentAt = "2026-07-15T13:00:00-04:00",
                        isUnread = true,
                        comedianId = COMEDIAN_UUID,
                    ),
                    NotificationItem(
                        id = "screenshot-notification-002",
                        title = "Your favorites have 2 new shows",
                        body = "The Comedy Cellar and The Bell House",
                        comedianName = "Taylor Tomlinson",
                        comedianImageUrl = "",
                        comedians =
                            listOf(
                                NotificationComedian(
                                    comedianId = COMEDIAN_UUID,
                                    comedianName = "Taylor Tomlinson",
                                    comedianImageUrl = "",
                                ),
                                NotificationComedian(
                                    comedianId = SECOND_COMEDIAN_UUID,
                                    comedianName = "Sam Jay",
                                    comedianImageUrl = "",
                                ),
                            ),
                        shows =
                            listOf(
                                NotificationShow(
                                    showId = SHOW_ID,
                                    subtitle = "The Bell House on Saturday at 8:00 PM",
                                    showDate = "2026-07-18T20:00:00-04:00",
                                    clubName = "The Bell House",
                                    city = "Brooklyn",
                                    state = "NY",
                                ),
                                NotificationShow(
                                    showId = SECOND_SHOW_ID,
                                    subtitle = "The Comedy Cellar on Sunday at 7:30 PM",
                                    showDate = "2026-07-19T19:30:00-04:00",
                                    clubName = "The Comedy Cellar",
                                    city = "New York",
                                    state = "NY",
                                ),
                            ),
                        channels = listOf("push"),
                        sentAt = "2026-07-14T15:00:00-04:00",
                        isUnread = false,
                        route = "favorites",
                    ),
                ),
            unreadCount = 1,
            lastSeenAt = "2026-07-14T16:00:00-04:00",
        )

    val notificationReferenceTime: ZonedDateTime = ZonedDateTime.parse("2026-07-15T15:00:00-04:00")
}
