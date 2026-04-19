import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";
import { FIXTURE_SHOWS_TONIGHT } from "./homeFixtures";

export async function getShowsTonight(): Promise<ShowDTO[]> {
    if (process.env.E2E_FIXTURE_MODE === "1") {
        return FIXTURE_SHOWS_TONIGHT;
    }

    const now = new Date();
    const startOfDay = new Date(now);
    startOfDay.setHours(0, 0, 0, 0);
    const endOfDay = new Date(now);
    endOfDay.setHours(23, 59, 59, 999);

    return findShowsForHome(
        { date: { gte: startOfDay, lte: endOfDay }, club: { visible: true } },
        { date: "asc" },
    );
}
