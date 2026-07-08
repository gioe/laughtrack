import { Prisma } from "@prisma/client";
import { LINEUP_COMEDIAN_SELECT } from "@/lib/data/comedian/lineupComedianSelect";
import { PARENT_COMEDIAN_LINEUP_SELECT } from "@/lib/data/comedian/parentComedianSelect";
import { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { computeDistanceMiles } from "@/util/distanceUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { computeShowSoldOut } from "@/util/show/soldOutUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";

// Single source of truth for the public show select + DTO mapper shared by the
// search data path (lib/data/show/search/findShowsWithCount.ts) and the home
// data path (lib/data/home/findShowsForHome.ts). Previously each file carried a
// near-identical copy of this select and mapping logic, so a lineup-visibility
// or tag-filter fix needed synchronized edits and silent drift changed what the
// API returned (T3.13, 2026-07-07 Full-Repo Audit). The two paths still differ
// deliberately — search adds `description` and a profileId-keyed
// favoriteComedians block to the select and emits description/popularityScore in
// the DTO; home derives imageUrl from the best lineup photo — so those
// differences are PARAMETERIZED (see buildShowSelect / MapShowRowOptions) rather
// than collapsed. DTO shapes are consumed by iOS/Android via the OpenAPI
// contract, so per-path field parity must stay exact.

// The comedian select nested under each lineup item, common to both paths. The
// search path spreads this and adds a favoriteComedians block (see
// buildShowSelect); home uses it as-is.
const LINEUP_ITEM_COMEDIAN_SELECT = {
    ...LINEUP_COMEDIAN_SELECT,
    _count: {
        select: {
            lineupItems: true,
        },
    },
    parentComedian: {
        select: {
            ...PARENT_COMEDIAN_LINEUP_SELECT,
            _count: {
                select: {
                    lineupItems: true,
                },
            },
        },
    },
} satisfies Prisma.ComedianSelect;

// The base public show select: the fields both the search and home paths fetch.
// Deliberate per-path additions (search: `description`, and a favoriteComedians
// block keyed by profileId) are layered on via buildShowSelect — do NOT add them
// here or the home path would fetch columns it never maps.
export const PUBLIC_SHOW_SELECT = {
    id: true,
    name: true,
    date: true,
    popularity: true,
    room: true,
    tickets: {
        select: {
            price: true,
            soldOut: true,
            purchaseUrl: true,
            type: true,
        },
    },
    club: {
        select: {
            id: true,
            name: true,
            address: true,
            city: true,
            state: true,
            zipCode: true,
            hasImage: true,
            timezone: true,
        },
    },
    lineupItems: {
        where: {
            comedian: {
                visible: true,
                taggedComedians: {
                    none: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        },
        select: {
            role: true,
            comedian: {
                select: LINEUP_ITEM_COMEDIAN_SELECT,
            },
        },
    },
    taggedShows: {
        where: { tag: { visibility: "PUBLIC" } },
        select: {
            tag: { select: { slug: true, name: true } },
        },
    },
} satisfies Prisma.ShowSelect;

interface BuildShowSelectOptions {
    /** Add `description: true` (search path fetches it; home does not). */
    includeDescription?: boolean;
    /**
     * When set, add a favoriteComedians block keyed by this profileId to the
     * lineup comedian select so the mapper can compute isFavorite. Only the
     * search path supplies this.
     */
    favoriteComediansProfileId?: string;
}

/**
 * Compose the show select for a path that needs the search-specific additions
 * (description column and/or a profileId-keyed favoriteComedians block) on top
 * of PUBLIC_SHOW_SELECT. Home passes PUBLIC_SHOW_SELECT directly.
 */
export function buildShowSelect(options: BuildShowSelectOptions = {}) {
    return {
        ...PUBLIC_SHOW_SELECT,
        ...(options.includeDescription ? { description: true } : {}),
        lineupItems: {
            ...PUBLIC_SHOW_SELECT.lineupItems,
            select: {
                role: true,
                comedian: {
                    select: {
                        ...LINEUP_ITEM_COMEDIAN_SELECT,
                        ...(options.favoriteComediansProfileId
                            ? {
                                  favoriteComedians: {
                                      where: {
                                          profileId:
                                              options.favoriteComediansProfileId,
                                      },
                                      select: {
                                          id: true,
                                      },
                                  },
                              }
                            : {}),
                    },
                },
            },
        },
    } satisfies Prisma.ShowSelect;
}

// Payload of a row loaded with PUBLIC_SHOW_SELECT. `description` is intersected
// as optional so both the home payload (no description column) and the search
// payload (description column present) are assignable. The favoriteComedians
// block the search path adds is read structurally inside filterAndMapLineupItems
// and does not need to appear in this type.
export type PublicShowRow = Prisma.ShowGetPayload<{
    select: typeof PUBLIC_SHOW_SELECT;
}> & { description?: string | null };

export interface MapShowRowOptions {
    /**
     * Passed to filterAndMapLineupItems to compute each lineup member's
     * isFavorite flag. Search supplies helper.getUserId(); home omits it.
     */
    userId?: string;
    /**
     * Zip the viewer searched from, used to compute distanceMiles. When absent,
     * `distanceWhenNoZip` controls whether the field is null (search) or
     * undefined (home).
     */
    zipCode?: string;
    /**
     * imageUrl derivation. "club" uses the club image only (search); "lineup"
     * uses the most-popular lineup comedian's image, falling back to the club
     * image (home).
     */
    imageSource?: "club" | "lineup";
    /** Emit `description` in the DTO (search only). */
    includeDescription?: boolean;
    /** Emit `popularityScore` in the DTO (search only). */
    includePopularityScore?: boolean;
    /**
     * `room` emission. "raw" passes show.room through, preserving null (search);
     * "coalesce" maps null → undefined (home).
     */
    room?: "raw" | "coalesce";
    /**
     * distanceMiles when `zipCode` is absent. "compute" still calls
     * computeDistanceMiles (yielding null — the search behavior); "undefined"
     * omits the computation (home behavior).
     */
    distanceWhenNoZip?: "compute" | "undefined";
}

/**
 * Map a PUBLIC_SHOW_SELECT row to a ShowDTO. Per-path differences are driven by
 * `options` so each caller reproduces its exact previous output — the field set
 * is part of the OpenAPI contract and must not drift between paths.
 */
export function mapShowRowToDTO(
    show: PublicShowRow,
    options: MapShowRowOptions = {},
): ShowDTO {
    const {
        userId,
        zipCode,
        imageSource = "club",
        includeDescription = false,
        includePopularityScore = false,
        room = "raw",
        distanceWhenNoZip = "compute",
    } = options;

    const lineup = filterAndMapLineupItems(show.lineupItems, userId);
    const clubImageUrl = buildClubImageUrl(show.club.name, show.club.hasImage);
    const imageUrl =
        imageSource === "lineup"
            ? (getBestLineupImageUrl(lineup) ?? clubImageUrl)
            : clubImageUrl;

    const distanceMiles =
        zipCode || distanceWhenNoZip === "compute"
            ? computeDistanceMiles(zipCode, show.club.zipCode)
            : undefined;

    return {
        id: show.id,
        date: show.date,
        name: show.name,
        ...(includePopularityScore
            ? { popularityScore: show.popularity }
            : {}),
        ...(includeDescription
            ? { description: show.description ?? undefined }
            : {}),
        room: room === "coalesce" ? (show.room ?? undefined) : show.room,
        address: show.club.address,
        clubId: show.club.id,
        clubName: show.club.name,
        clubCity: show.club.city,
        clubState: show.club.state,
        imageUrl,
        soldOut: computeShowSoldOut(show.name, show.tickets),
        lineup,
        tickets: mapTickets(show.tickets),
        distanceMiles,
        timezone: show.club.timezone,
        tags: mapShowTags(show.taggedShows),
    };
}

function mapShowTags(
    taggedShows: PublicShowRow["taggedShows"] | null | undefined,
): ShowDTO["tags"] {
    return (taggedShows ?? [])
        .map((tt) => tt.tag)
        .filter(
            (tag): tag is { slug: string; name: string } =>
                typeof tag?.slug === "string" && typeof tag?.name === "string",
        )
        .map((tag) => ({ slug: tag.slug, name: tag.name }));
}

/**
 * Pick the image of the most-popular lineup comedian that has one, falling back
 * to null when no lineup member has an image. Popularity is the comedian's
 * showCount (see getLineupItemPopularity).
 */
export function getBestLineupImageUrl(
    lineup: ComedianLineupDTO[],
): string | null {
    let best: ComedianLineupDTO | null = null;
    for (const comedian of lineup) {
        if (!comedian.imageUrl) continue;
        if (
            !best ||
            getLineupItemPopularity(comedian) > getLineupItemPopularity(best)
        ) {
            best = comedian;
        }
    }
    return best?.imageUrl ?? null;
}

export function getLineupItemPopularity(comedian: ComedianLineupDTO): number {
    return comedian.showCount ?? 0;
}
