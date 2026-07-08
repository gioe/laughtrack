import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { findShowsForHome } from "./findShowsForHome";

export async function getShowsNearZip(
    zipCode: string,
    radius?: number,
): Promise<ShowDTO[]> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const now = new Date();
    const nearbyZips = resolveNearbyZips(zipCode, radius);

    return findShowsForHome(
        {
            date: { gte: now },
            club: { visible: true, zipCode: { in: nearbyZips } },
        },
        [{ popularity: "desc" }, { date: "asc" }],
        8,
        { zipCode, sortByHomeRelevance: true },
    );
}
