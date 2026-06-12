import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { isOpenMicShow, type OpenMicShowLike } from "./isOpenMicShow";

export interface HeroImageShowLike extends OpenMicShowLike {
    imageUrl: string;
    lineup?: ComedianLineupDTO[];
}

// The lineup item we treat as the headliner for hero-image selection. Mirrors
// iOS ShowDetailPresentation.headliner (ShowDetailView.swift) so both clients
// pick the same comedian: the API has no role field on lineup, so approximate
// by highest socialData.popularity, breaking ties by showCount then list
// position. Missing socialData ranks as -1 (below an explicit popularity of
// 0), matching the Swift `?? -1`. Returns null for open mics and empty
// lineups. Selection only — never surface a "Headliner" label in UI copy.
export function inferHeadliner(
    show: HeroImageShowLike,
): ComedianLineupDTO | null {
    if (isOpenMicShow(show)) return null;
    const lineup = show.lineup ?? [];
    if (lineup.length === 0) return null;

    return lineup
        .map((comedian, position) => ({ comedian, position }))
        .sort((a, b) => {
            const aPop = a.comedian.socialData?.popularity ?? -1;
            const bPop = b.comedian.socialData?.popularity ?? -1;
            if (aPop !== bPop) return bPop - aPop;
            const aCount = a.comedian.showCount ?? 0;
            const bCount = b.comedian.showCount ?? 0;
            if (aCount !== bCount) return bCount - aCount;
            return a.position - b.position;
        })[0].comedian;
}

export interface ShowHeroImage {
    src: string;
    // Set only when `src` is the headliner's headshot — callers use it for
    // alt text. Null whenever the club image won the fallback.
    headliner: ComedianLineupDTO | null;
}

// Hero image: prefer the inferred headliner's headshot when present, fall
// back to the show's own image (the club image) otherwise. Mirrors iOS
// ShowDetailPresentation.heroImageURL. Comedians without an image carry an
// empty imageUrl (buildComedianImageUrl returns "" when hasImage is false),
// which falls through to the show image just like the Swift isEmpty check.
export function showHeroImage(show: HeroImageShowLike): ShowHeroImage {
    const headliner = inferHeadliner(show);
    const headshot = headliner?.imageUrl?.trim();
    if (headliner && headshot) {
        return { src: headshot, headliner };
    }
    return { src: show.imageUrl, headliner: null };
}
