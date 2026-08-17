import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { inferHeadliner } from "@/util/show/showHeroImage";
import { findShowsForHome } from "./findShowsForHome";

const TRENDING_SHOW_LIMIT = 8;
const TRENDING_SHOW_CANDIDATE_TAKE = 50;

function selectDiverseShows(shows: readonly ShowDTO[]): ShowDTO[] {
    const selected: ShowDTO[] = [];
    const repeatedHeadliners: ShowDTO[] = [];
    const seenHeadlinerIDs = new Set<number>();

    for (const show of shows) {
        const headlinerID = inferHeadliner(show)?.id;
        if (headlinerID === undefined || !seenHeadlinerIDs.has(headlinerID)) {
            selected.push(show);
            if (headlinerID !== undefined) seenHeadlinerIDs.add(headlinerID);
            if (selected.length === TRENDING_SHOW_LIMIT) return selected;
        } else {
            repeatedHeadliners.push(show);
        }
    }

    return selected.concat(repeatedHeadliners).slice(0, TRENDING_SHOW_LIMIT);
}

export async function getTrendingShowsThisWeek(
    timezone: string = "UTC",
    zipCode?: string,
    radius?: number,
): Promise<ShowDTO[]> {
    const now = new Date();
    // Lower bound stays at instant-now (asymmetric with the upper bound) to
    // exclude shows that have already started; upper bound anchors on a
    // calendar day in the caller's TZ rather than a 168h-from-now wallclock
    // instant so day-7 evening shows are in the window regardless of when in
    // the day the call lands.
    const weekOutInTz = toZonedTime(now, timezone);
    weekOutInTz.setDate(weekOutInTz.getDate() + 7);
    const weekOutDate = format(weekOutInTz, "yyyy-MM-dd");
    const endOfWeekDay = fromZonedTime(`${weekOutDate}T23:59:59.999`, timezone);
    const nearbyZips =
        zipCode && /^\d{5}(-\d{4})?$/.test(zipCode)
            ? resolveNearbyZips(zipCode, radius)
            : null;

    const candidates = await findShowsForHome(
        {
            date: { gte: now, lte: endOfWeekDay },
            club: {
                visible: true,
                ...(nearbyZips ? { zipCode: { in: nearbyZips } } : {}),
            },
        },
        { popularity: "desc" },
        TRENDING_SHOW_CANDIDATE_TAKE,
        nearbyZips ? { zipCode } : {},
    );

    return selectDiverseShows(candidates);
}
