import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

export async function getTrendingShowsThisWeek(
    timezone: string = "UTC",
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

    return findShowsForHome(
        { date: { gte: now, lte: endOfWeekDay }, club: { visible: true } },
        { popularity: "desc" },
    );
}
