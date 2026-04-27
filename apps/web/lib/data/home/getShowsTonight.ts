import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

export async function getShowsTonight(): Promise<ShowDTO[]> {
    const now = new Date();
    const startOfDay = new Date(now);
    startOfDay.setUTCHours(0, 0, 0, 0);
    const endOfDay = new Date(now);
    endOfDay.setUTCHours(23, 59, 59, 999);

    return findShowsForHome(
        { date: { gte: startOfDay, lte: endOfDay }, club: { visible: true } },
        { date: "asc" },
    );
}
