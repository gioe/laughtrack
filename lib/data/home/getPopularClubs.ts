import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function getPopularClubs(userId?: string): Promise<ClubDTO[]> {
    return db.club
        .findMany({
            select: {
                id: true,
                address: true,
                zipCode: true,
                name: true,
                shows: {
                    where: {
                        date: {
                            gte: new Date(),
                            lte: new Date(
                                Date.now() + 30 * 24 * 60 * 60 * 1000,
                            ), // 30 days from now
                        },
                    },
                    select: {
                        lineupItems: {
                            select: {
                                comedianId: true,
                            },
                        },
                    },
                },
            },
            take: 8,
        })
        .then((clubs) =>
            clubs.map((club) => ({
                id: club.id,
                address: club.address,
                name: club.name,
                zipCode: club.zipCode,
                imageUrl: buildClubImageUrl(club.name),
                active_comedian_count: new Set(
                    club.shows.flatMap((show) =>
                        show.lineupItems.map((item) => item.comedianId),
                    ),
                ).size,
            })),
        );
}
