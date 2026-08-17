import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { findShowsForHome } from "./findShowsForHome";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    selectDiverseShowsByTime,
} from "./showRailSelection";

export async function getShowsTonight(
    timezone: string = "UTC",
    zipCode?: string,
    radius?: number,
): Promise<ShowDTO[]> {
    // West Coast users hitting "tonight" in the morning local were getting
    // tomorrow's UTC day until this anchored on the caller's wallclock date.
    const todayInTz = format(toZonedTime(new Date(), timezone), "yyyy-MM-dd");
    const startOfDay = fromZonedTime(`${todayInTz}T00:00:00`, timezone);
    const endOfDay = fromZonedTime(`${todayInTz}T23:59:59.999`, timezone);
    const nearbyZips =
        zipCode && /^\d{5}(-\d{4})?$/.test(zipCode)
            ? resolveNearbyZips(zipCode, radius)
            : null;

    const candidates = await findShowsForHome(
        {
            date: { gte: startOfDay, lte: endOfDay },
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
