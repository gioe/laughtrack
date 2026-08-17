import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { findShowsForHome } from "./findShowsForHome";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    selectDiverseShowsByTime,
} from "./showRailSelection";

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
        [{ date: "asc" }, { id: "asc" }],
        HOME_SHOW_RAIL_CANDIDATE_LIMIT,
        nearbyZips
            ? { zipCode, sortByHomeRelevance: false, requireLineup: true }
            : { sortByHomeRelevance: false, requireLineup: true },
    );

    return selectDiverseShowsByTime(candidates);
}
