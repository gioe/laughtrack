import { db } from "@/lib/db";

export async function toggleFavorite(
    comedianUuid: string,
    userId: string,
    setFavorite: boolean,
): Promise<boolean> {
    if (setFavorite) {
        // Upsert to avoid P2002 unique-constraint violation on retry/concurrent calls
        await db.favoriteComedian.upsert({
            where: {
                profileId_comedianId: {
                    profileId: userId,
                    comedianId: comedianUuid,
                },
            },
            create: { profileId: userId, comedianId: comedianUuid },
            update: {},
        });
        return true;
    } else {
        // Remove favorite record
        await db.favoriteComedian.deleteMany({
            where: {
                comedianId: comedianUuid,
                profileId: userId,
            },
        });
        return false;
    }
}
