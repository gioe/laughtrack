import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";
import { FIXTURE_SHOWS_TRENDING } from "./homeFixtures";

export async function getTrendingShowsThisWeek(): Promise<ShowDTO[]> {
    if (process.env.E2E_FIXTURE_MODE === "1") {
        return FIXTURE_SHOWS_TRENDING;
    }

    const now = new Date();
    const weekFromNow = new Date(now);
    weekFromNow.setDate(weekFromNow.getDate() + 7);

    return findShowsForHome(
        { date: { gte: now, lte: weekFromNow }, club: { visible: true } },
        { popularity: "desc" },
    );
}
