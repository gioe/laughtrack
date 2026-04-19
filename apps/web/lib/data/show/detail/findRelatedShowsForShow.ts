import { findShowsForHome } from "@/lib/data/home/findShowsForHome";
import { ShowDTO } from "@/objects/class/show/show.interface";

const RELATED_LIMIT = 4;

// Next upcoming shows at the same club, excluding the show itself.
// Reuses `findShowsForHome` for the shared select + mapper.
export async function findRelatedShowsForShow(
    showId: number,
    clubId: number,
): Promise<ShowDTO[]> {
    return findShowsForHome(
        {
            id: { not: showId },
            date: { gte: new Date() },
            club: { id: clubId, visible: true },
        },
        [{ date: "asc" }, { id: "asc" }],
        RELATED_LIMIT,
    );
}
