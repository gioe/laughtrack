import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";

const MAX_CLUBS_LIMIT = 100;

export async function getClubs(limit = 8, offset = 0): Promise<ClubDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_CLUBS_LIMIT);
    return db.club
        .findMany({
            where: { status: "active" },
            orderBy: { id: "asc" }, // stable insertion-order sort for offset pagination
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
            take: safeLimit,
            skip: offset,
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
