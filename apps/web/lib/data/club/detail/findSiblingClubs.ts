import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";

export interface SiblingClubDTO {
    id: number;
    name: string;
    city: string | null;
    state: string | null;
    imageUrl: string;
}

export async function findSiblingClubs(
    chainId: number,
    excludeClubId: number,
): Promise<SiblingClubDTO[]> {
    const clubs = await db.club.findMany({
        where: {
            chainId,
            id: { not: excludeClubId },
            visible: true,
        },
        select: {
            id: true,
            name: true,
            city: true,
            state: true,
            hasImage: true,
        },
        orderBy: { name: "asc" },
    });

    return clubs.map((c) => ({
        id: c.id,
        name: c.name,
        city: c.city,
        state: c.state,
        imageUrl: buildClubImageUrl(c.name, c.hasImage),
    }));
}
