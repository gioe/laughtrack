import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

export async function getTrendingShowsThisWeek(): Promise<ShowDTO[]> {
    const now = new Date();
    const weekFromNow = new Date(now);
    weekFromNow.setDate(weekFromNow.getDate() + 7);

    return findShowsForHome(
        { date: { gte: now, lte: weekFromNow }, club: { visible: true } },
        { popularity: "desc" },
    );
}
