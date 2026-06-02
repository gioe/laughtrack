import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

const MAX_CLUBS_LIMIT = 100;

interface GetClubsOptions {
    requireImage?: boolean;
}

export async function getClubs(
    limit = 8,
    offset = 0,
    options: GetClubsOptions = {},
): Promise<ClubDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_CLUBS_LIMIT);
    const now = new Date();
    // Hide clubs with no upcoming shows from discovery surfaces (home carousel,
    // iOS /api/v1/clubs, /api/v1/home/feed). Matches the default behavior of
    // findClubsWithCount (club search) — see docs/design/empty-club-discovery-policy.md.
    // Dormant clubs remain reachable at /club/[name] for deep links/SEO.
    const where: Prisma.ClubWhereInput = {
        status: "active",
        ...(options.requireImage && { hasImage: true }),
        shows: { some: { date: { gt: now } } },
    };

    return db.club
        .findMany({
            where,
            orderBy: { id: "asc" }, // stable insertion-order sort for offset pagination
            select: {
                id: true,
                address: true,
                zipCode: true,
                name: true,
                hasImage: true,
                shows: {
                    where: {
                        date: {
                            gte: now,
                            lte: new Date(
                                now.getTime() + 30 * 24 * 60 * 60 * 1000,
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
                imageUrl: buildClubImageUrl(club.name, club.hasImage),
                activeComedianCount: new Set(
                    club.shows.flatMap((show) =>
                        show.lineupItems.map((item) => item.comedianId),
                    ),
                ).size,
            })),
        );
}
