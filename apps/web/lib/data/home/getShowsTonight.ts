import zipcodes from "zipcodes";
import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
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
            ? resolveZipCodes(zipCode, radius)
            : null;

    return findShowsForHome(
        {
            date: { gte: startOfDay, lte: endOfDay },
            club: {
                visible: true,
                ...(nearbyZips ? { zipCode: { in: nearbyZips } } : {}),
            },
        },
        { date: "asc" },
    );
}
