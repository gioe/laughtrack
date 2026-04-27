import { fromZonedTime, toZonedTime, format } from "date-fns-tz";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

export async function getShowsTonight(
    timezone: string = "UTC",
): Promise<ShowDTO[]> {
    // West Coast users hitting "tonight" in the morning local were getting
    // tomorrow's UTC day until this anchored on the caller's wallclock date.
    const todayInTz = format(toZonedTime(new Date(), timezone), "yyyy-MM-dd");
    const startOfDay = fromZonedTime(`${todayInTz}T00:00:00`, timezone);
    const endOfDay = fromZonedTime(`${todayInTz}T23:59:59.999`, timezone);

    return findShowsForHome(
        { date: { gte: startOfDay, lte: endOfDay }, club: { visible: true } },
        { date: "asc" },
    );
}
