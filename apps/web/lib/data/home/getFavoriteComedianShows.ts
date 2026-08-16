import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { findShowsForHome } from "./findShowsForHome";

export async function getFavoriteComedianShows(
    profileId?: string | null,
    zipCode?: string | null,
    radius?: number,
): Promise<ShowDTO[]> {
    if (!profileId) {
        return [];
    }

    const usableZipCode =
        zipCode && /^\d{5}(-\d{4})?$/.test(zipCode) ? zipCode : null;
    const nearbyZips = usableZipCode
        ? resolveNearbyZips(usableZipCode, radius)
        : null;

    return findShowsForHome(
        {
            date: { gte: new Date() },
            club: {
                visible: true,
                ...(nearbyZips ? { zipCode: { in: nearbyZips } } : {}),
            },
            lineupItems: {
                some: {
                    comedian: {
                        visible: true,
                        OR: [
                            {
                                favoriteComedians: {
                                    some: { profileId },
                                },
                            },
                            {
                                parentComedian: {
                                    visible: true,
                                    favoriteComedians: {
                                        some: { profileId },
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        },
        [{ popularity: "desc" }, { date: "asc" }, { id: "asc" }],
        8,
        usableZipCode ? { profileId, zipCode: usableZipCode } : { profileId },
    );
}
