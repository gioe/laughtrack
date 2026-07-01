import { db } from "@/lib/db";

export interface HomeClubFilterDTO {
    // Stringified club id carried in the `homeClub` URL param. Stable identifier
    // the <select> binds to. Unlike home city there is no composite token — a
    // club id is already unique — so no encode/decode helper is needed.
    value: string;
    // Club name, e.g. "The Comedy Store".
    label: string;
    // Number of visible, non-alias comedians based at this club.
    count: number;
}

// Clubs with fewer than this many based comedians are omitted so the dropdown
// stays meaningful. Lower than the home-city threshold because the population
// per club is naturally much smaller than per city. The filter still works for
// an omitted club via a hand-edited URL param.
export const MIN_COMEDIANS_PER_HOME_CLUB = 2;

/**
 * Distinct comedian home clubs for the comedian-search location filter, grouped
 * by homeClubId and ordered by comedian count desc (most active home rooms
 * first, matching the home-city filter convention). Returns [] when no comedian
 * has a derived home club — the FilterBar omits the control entirely in that
 * case.
 *
 * Parallels getComedianHomeCityFilters, with one extra step: homeClubId is an
 * FK, so the label (club name) is not on the comedian row and is resolved in a
 * single follow-up lookup over the qualifying club ids.
 */
export async function getComedianHomeClubFilters(): Promise<
    HomeClubFilterDTO[]
> {
    const groups = await db.comedian.groupBy({
        by: ["homeClubId"],
        where: {
            visible: true,
            parentComedian: { is: null },
            homeClubId: { not: null },
            taggedComedians: {
                none: { tag: { restrictContent: true } },
            },
        },
        _count: { _all: true },
    });

    const qualifying = groups.filter(
        (g): g is typeof g & { homeClubId: number } =>
            g.homeClubId !== null &&
            g._count._all >= MIN_COMEDIANS_PER_HOME_CLUB,
    );
    if (qualifying.length === 0) {
        return [];
    }

    const clubIds = qualifying.map((g) => g.homeClubId);
    const clubs = await db.club.findMany({
        where: { id: { in: clubIds } },
        select: { id: true, name: true },
    });
    const nameById = new Map(clubs.map((c) => [c.id, c.name]));

    return qualifying
        .map((g) => ({
            value: String(g.homeClubId),
            label: nameById.get(g.homeClubId) ?? `Club ${g.homeClubId}`,
            count: g._count._all,
        }))
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}
