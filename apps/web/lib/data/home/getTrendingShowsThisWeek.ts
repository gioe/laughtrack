import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import zipcodes from "zipcodes";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

function resolveZipCodes(zipCode: string, radius?: number): string[] {
    if (!radius || radius < 1 || radius > 500) return [zipCode];
    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];
        return results.map((z: string | zipcodes.ZipCode) =>
            typeof z === "string" ? z : z.zip,
        );
    } catch {
        return [zipCode];
    }
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
            ? resolveZipCodes(zipCode, radius)
            : null;

    return findShowsForHome(
        {
            date: { gte: now, lte: endOfWeekDay },
            club: {
                visible: true,
                ...(nearbyZips ? { zipCode: { in: nearbyZips } } : {}),
            },
        },
        { popularity: "desc" },
        undefined,
        nearbyZips ? { zipCode } : {},
    );
}
