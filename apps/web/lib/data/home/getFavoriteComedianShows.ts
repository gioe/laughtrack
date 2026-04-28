import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

export async function getFavoriteComedianShows(
    profileId?: string | null,
): Promise<ShowDTO[]> {
    if (!profileId) {
        return [];
    }

    return findShowsForHome(
        {
            date: { gte: new Date() },
            club: { visible: true },
            lineupItems: {
                some: {
                    comedian: {
                        favoriteComedians: {
                            some: { profileId },
                        },
                    },
                },
            },
        },
        [{ date: "asc" }, { popularity: "desc" }],
        8,
    );
}
