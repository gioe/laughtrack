package app.laughtrack.android.screenshots

import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.core.data.profile.ProfileAccount
import app.laughtrack.android.core.data.profile.ProfilePreferences
import app.laughtrack.android.core.data.savedshows.SavedShowsCollection
import app.laughtrack.android.core.data.savedshows.SavedShowsSnapshot
import app.laughtrack.android.core.network.generated.model.ComedianSearchItem
import app.laughtrack.android.core.network.generated.model.FavoriteClubItem
import app.laughtrack.android.core.network.generated.model.FavoritePodcastItem
import app.laughtrack.android.core.network.generated.model.NotificationComedian
import app.laughtrack.android.core.network.generated.model.NotificationItem
import app.laughtrack.android.core.network.generated.model.NotificationListResponseData
import app.laughtrack.android.core.network.generated.model.NotificationShow
import app.laughtrack.android.core.network.generated.model.Show
import app.laughtrack.android.core.network.generated.model.SocialData
import app.laughtrack.android.core.network.generated.model.Ticket
import app.laughtrack.android.feature.profile.ProfileUiState
import java.math.BigDecimal
import java.time.ZonedDateTime

/**
 * Credentials-free, immutable content for authenticated screenshot captures.
 *
 * The persona never enters the authentication or API layers. It is passed
 * explicitly by screenshot tests; production navigation continues to use the
 * Hilt-backed screen models. Visible saved shows use direct production CDN
 * portraits, while an image-less show retains deterministic fallback coverage.
 */
object AuthenticatedScreenshotPersona {
    const val COMEDIAN_UUID = "00000000-0000-4000-8000-000000000101"
    const val SECOND_COMEDIAN_UUID = "00000000-0000-4000-8000-000000000102"
    const val COMEDIAN_ID = 910_001
    const val SECOND_COMEDIAN_ID = 910_002
    const val SHOW_ID = 910_101
    const val SECOND_SHOW_ID = 910_102
    const val UPCOMING_SAVED_SHOW_ID = 910_103
    const val UPCOMING_SAVED_SHOW_TITLE = "Atsuko Okatsuka: Full Grown Tour"

    private val upcomingSavedShows =
        listOf(
            savedShow(
                id = 910_103,
                date = "2026-08-21T20:00:00-04:00",
                name = UPCOMING_SAVED_SHOW_TITLE,
                clubName = "Town Hall",
                clubCity = "New York",
                imageUrl = "https://laughtrack.b-cdn.net/comedians/Atsuko%20Okatsuka.png",
            ),
            savedShow(
                id = 910_104,
                date = "2026-08-24T20:00:00-04:00",
                name = "Josh Johnson and Friends",
                clubName = "The Bell House",
                clubCity = "Brooklyn",
                imageUrl = "https://laughtrack.b-cdn.net/comedians/Josh%20Johnson.png",
            ),
            savedShow(
                id = 910_105,
                date = "2026-08-28T20:00:00-04:00",
                name = "Taylor Tomlinson Live",
                clubName = "The Comedy Cellar",
                clubCity = "New York",
                imageUrl =
                    "https://laughtrack.b-cdn.net/comedian-images/903740/" +
                        "79e27d03-1143-4633-a42f-f5569040fb44/avatar.jpg",
            ),
            savedShow(
                id = 910_106,
                date = "2026-09-02T19:30:00-04:00",
                name = "Sam Jay: Testing Material",
                clubName = "Union Hall",
                clubCity = "Brooklyn",
                imageUrl = "https://laughtrack.b-cdn.net/comedians/Sam%20Jay.png",
            ),
            savedShow(
                id = 910_107,
                date = "2026-09-05T20:00:00-04:00",
                name = "Mike Birbiglia: Please Stop the Ride",
                clubName = "Beacon Theatre",
                clubCity = "New York",
                imageUrl =
                    "https://laughtrack.b-cdn.net/comedian-images/246654/" +
                        "da23a0ff-061c-4a8b-82b8-e8b197615ad7/avatar.jpg",
            ),
            savedShow(
                id = 910_108,
                date = "2026-09-08T20:00:00-04:00",
                name = "Michelle Wolf and Friends",
                clubName = "Gotham Comedy Club",
                clubCity = "New York",
            ),
        )

    val profileUiState =
        ProfileUiState(
            signedIn = true,
            account =
                ProfileAccount(
                    displayName = "Jordan Rivera",
                    email = "jordan.rivera@example.com",
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
            values = upcomingSavedShows.associate { it.id to true },
            upcoming =
                SavedShowsCollection(
                    shows = upcomingSavedShows,
                    page = 1,
                    total = upcomingSavedShows.size,
                    totalPages = 2,
                ),
        )

    private fun savedShow(
        id: Int,
        date: String,
        name: String,
        clubName: String,
        clubCity: String,
        imageUrl: String = "",
    ) = Show(
        id = id,
        clubId = id + 1_000,
        date = date,
        imageUrl = imageUrl,
        clubName = clubName,
        clubCity = clubCity,
        clubState = "NY",
        tickets =
            listOf(
                Ticket(
                    price = BigDecimal("30"),
                    purchaseUrl = "https://laughtrack.app/screenshot/tickets/$id",
                    soldOut = false,
                    type = "General admission",
                ),
            ),
        name = name,
        soldOut = false,
        timezone = "America/New_York",
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
                                    id = COMEDIAN_ID,
                                    comedianId = COMEDIAN_UUID,
                                    comedianName = "Taylor Tomlinson",
                                    comedianImageUrl = "",
                                    showIds = listOf(SHOW_ID),
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
                                    id = COMEDIAN_ID,
                                    comedianId = COMEDIAN_UUID,
                                    comedianName = "Taylor Tomlinson",
                                    comedianImageUrl = "",
                                    showIds = listOf(SHOW_ID),
                                ),
                                NotificationComedian(
                                    id = SECOND_COMEDIAN_ID,
                                    comedianId = SECOND_COMEDIAN_UUID,
                                    comedianName = "Sam Jay",
                                    comedianImageUrl = "",
                                    showIds = listOf(SECOND_SHOW_ID),
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
