import { db } from "@/lib/db";

export async function toggleFavoriteClub(
    clubId: number,
    profileId: string,
    setFavorite: boolean,
): Promise<boolean> {
    if (setFavorite) {
        // Upsert to avoid P2002 unique-constraint violation on retry/concurrent calls
        await db.favoriteClub.upsert({
            where: {
                profileId_clubId: {
                    profileId,
                    clubId,
                },
            },
            create: { profileId, clubId },
            update: {},
        });
        return true;
    } else {
        // Remove favorite record (deleteMany so 0-row deletes are idempotent)
        await db.favoriteClub.deleteMany({
            where: {
                clubId,
                profileId,
            },
        });
        return false;
    }
}
