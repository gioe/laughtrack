/**
 * Client-facing feature kill-switches.
 *
 * These gate user-visible UI only — the underlying data fetching and the
 * `/api/v1` contract stay wired regardless. Flip a flag to `true` to re-expose
 * the surface once its data is trusted.
 */

/**
 * Comedian "home location" UI — the detail-header "Based in / Home club" pills
 * and the comedian-search home-city filter. Suppressed while the derived
 * home-location data is still unreliable. Mirrors the native clients' kill
 * switches (iOS `ComedianHomeLocationPresentation.isUIEnabled`, Android
 * `ComedianDetailScreen`'s `HOME_LOCATION_UI_ENABLED`).
 */
export const HOME_LOCATION_UI_ENABLED = false;
