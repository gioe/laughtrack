/**
 * Rail-card width tokens shared by the home-page carousels (shows, clubs) so
 * all rails scroll to one rhythm. Single source of truth: tailwind.config.ts
 * imports these for the `w-rail-card-compact` / `w-rail-card-standard` width
 * tokens, and the rails import them for scroll-distance math — keeping CSS
 * and JS card widths from drifting apart.
 *
 * compact applies on xs viewports (< 576px); standard applies from the
 * project `sm` breakpoint up (see tailwind.config.ts `theme.screens` — the
 * breakpoints are ranges, so rails must chain sm:/md:/lg: overrides).
 */
export const RAIL_CARD_COMPACT_WIDTH_PX = 280;
export const RAIL_CARD_STANDARD_WIDTH_PX = 320;
/** Matches `gap-4` on the rail scrollers. */
export const RAIL_CARD_GAP_PX = 16;
/**
 * Viewport min-width at which rails switch from compact to standard cards.
 * Mirrors the `sm` screen's min in tailwind.config.ts (576px) — NOT
 * Tailwind's default 640px sm breakpoint.
 */
export const RAIL_CARD_STANDARD_MIN_VIEWPORT_PX = 576;
