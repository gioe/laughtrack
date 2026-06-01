import type { ShowTagDTO } from "@/lib/data/show/detail/interface";

// Canonical slug for the "open mic" tag — a literal SPACE, not a kebab.
// TASK-2546 normalized every open-mic-flavored tag onto a single row
// (tags.id=1, slug='open mic'); this constant is the only place the literal
// appears so a future rename hits one site, not every branch in the UI.
export const OPEN_MIC_SLUG = "open mic";

export interface OpenMicShowLike {
    // Matches ShowDetailDTO.tags exactly — `undefined` when no tags hydrate,
    // never `null`. Keep this in lockstep with `ShowDetailDTO.tags` so callers
    // can't accidentally pass shapes the producer never emits.
    tags?: readonly ShowTagDTO[];
}

// isOpenMicShow — true when the show carries the canonical "open mic" tag.
export function isOpenMicShow(show: OpenMicShowLike): boolean {
    return (show.tags ?? []).some((t) => t.slug === OPEN_MIC_SLUG);
}
