import { db } from "@/lib/db";
import { encodeHomeCityToken } from "@/objects/class/query/QueryHelper";

export interface HomeCityFilterDTO {
    // `city|state` token carried in the `homeCity` URL param (see
    // encodeHomeCityToken). Stable identifier the <select> binds to.
    value: string;
    // Human label, e.g. "New York, NY" or "Rotterdam, Netherlands".
    label: string;
    // Number of visible, non-alias comedians based in this city.
    count: number;
}

// Cities with fewer than this many based comedians are omitted so the dropdown
// stays a usable length (~160 entries instead of the full ~250 long tail). The
// filter still works for an omitted city via a hand-edited URL param.
export const MIN_COMEDIANS_PER_HOME_CITY = 3;

/**
 * Distinct comedian home cities for the comedian-search location filter,
 * grouped by (homeCity, homeState) so same-named cities in different states
 * stay separate, ordered by comedian count desc (most active scenes first,
 * matching the club chain filter convention). Returns [] when no comedian has a
 * derived home city — the FilterBar omits the control entirely in that case.
 */
export async function getComedianHomeCityFilters(): Promise<
    HomeCityFilterDTO[]
> {
    const groups = await db.comedian.groupBy({
        by: ["homeCity", "homeState"],
        where: {
            visible: true,
            parentComedian: { is: null },
            homeCity: { not: null },
            taggedComedians: {
                none: { tag: { restrictContent: true } },
            },
        },
        _count: { _all: true },
    });

    return groups
        .map((g) => {
            const city = (g.homeCity ?? "").trim();
            const state = (g.homeState ?? "").trim() || null;
            return {
                city,
                value: encodeHomeCityToken(city, state),
                label: state ? `${city}, ${state}` : city,
                count: g._count._all,
            };
        })
        .filter((g) => g.city !== "" && g.count >= MIN_COMEDIANS_PER_HOME_CITY)
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
        .map(({ value, label, count }) => ({ value, label, count }));
}
