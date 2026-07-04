# iOS Refresh Behavior

This note tracks the main iOS surfaces that can issue API calls from foreground,
view-appearance, or explicit user refresh paths.

## App Foreground

- `LaughTrackApp` observes `scenePhase` and calls `ForegroundLocationRefresher.refreshIfEligible()` when the app becomes active.
- Network path: `PATCH /v1/me/location`, through `ProfileLocationPreferenceSyncClient`.
- Guardrails: only runs for a saved geolocated ZIP, only when location is already authorized, coalesces one in-flight refresh, and skips the write when the ZIP has not changed.

## Discover And Home

- `HomeView` rails use `.task(id:)` keyed by ZIP and distance.
- Network path: `GET /v1/home-feed`.
- Cache policy: `HomeFeedRequestCoalescer` dedupes in-flight requests; `MainPageCache` reads and writes app-level memory cache plus `PersistentMainPageCache` for home feed and favorite-show rails. The default TTL is one hour.

## Search And Pinned Lists

- `ShowsListView`, `ComediansDiscoveryView`, and `ClubsDiscoveryView` use `.task(id:)` keyed by active query state.
- Network paths: `GET /v1/shows/search`, `GET /v1/comedians/search`, and `GET /v1/clubs/search`.
- Cache policy: search models read and write the app-level `DataCache<LaughTrackCacheKey>` per query and page. `loadMore` remains explicit pagination, and query changes still revalidate the requested first page.
- Pinned lists inside club and comedian detail use the same `ShowsListView` path with pinned club or comedian filters.

## Entity Detail

- Show, comedian, club, and podcast detail screens load from `.task` via `loadIfNeeded`.
- Network paths:
  - `GET /v1/shows/{id}`
  - `GET /v1/comedians/{id}`
  - `GET /v1/comedians/{id}/upcoming-runs`
  - `GET /v1/comedians/{id}/co-bill`
  - `GET /v1/clubs/{id}`
  - `GET /v1/shows/search` for club related shows
  - `GET /v1/podcasts/{id}`
- Cache policy: automatic `loadIfNeeded` can reuse app-level memory cache across recreated detail model instances. Explicit retry/reload still performs a network request and refreshes the cache.

## Podcast Tonight Near You

- `PodcastTonightNearYouCard` loads when its podcast ID or ZIP changes.
- Network paths: `GET /v1/podcasts/{id}` and `GET /v1/home-feed`.
- Cache policy: reuses the podcast detail cache and the home-feed cache before calling the network; the home-feed network path still goes through the shared in-flight coalescer.

## Critical Freshness Paths

- Favorite add/remove operations still call their mutation endpoints immediately.
- Detail retry buttons call `reload`, which bypasses cached detail reads and refreshes the cache from the network.
- Search query changes and pagination remain explicit fetch paths keyed by query/page.
- Notification center open still reloads notifications and marks them seen; it is intentionally not cached because it drives unread state.
