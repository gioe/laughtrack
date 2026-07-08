import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";

const MAX_CLUBS_LIMIT = 100;

interface GetClubsByZipOptions {
    requireImage?: boolean;
}

// ZIP-scoped sibling of getClubs(). Powers the "Popular clubs near you" home
// rail so it re-localizes when the viewer changes their zip, the same way the
// comedian and show rails do. Falls back to the global getClubs() list at the
// call site when no zip resolves or no nearby clubs are found.
export async function getClubsByZip(
    zipCode: string,
    radius?: number,
    limit = 8,
    options: GetClubsByZipOptions = {},
): Promise<ClubDTO[]> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const safeLimit = Math.min(Math.max(1, limit), MAX_CLUBS_LIMIT);
    const now = new Date();
    const nearbyZips = resolveNearbyZips(zipCode, radius);

    // Mirrors getClubs() discovery rules (active, requires upcoming shows,
    // optionally requires an image) plus a zip-proximity filter.
    const where: Prisma.ClubWhereInput = {
        status: "active",
        zipCode: { in: nearbyZips },
        ...(options.requireImage && { hasImage: true }),
        shows: { some: { date: { gt: now } } },
    };

    return db.club
        .findMany({
            where,
            orderBy: { id: "asc" }, // stable insertion-order sort, matches getClubs()
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
