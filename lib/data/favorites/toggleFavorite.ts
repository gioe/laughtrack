
import { db } from "@/lib/db"

export async function toggleFavorite(comedianUuid: string,
    profileId: string,
    setFavorite: boolean): Promise<boolean> {
    if (setFavorite) {
        // Create favorite record
        await db.favoriteComedian.create({
            data: {
                comedianId: comedianUuid,
                profileId: profileId
            },
            select: {
                id: true
            }
        });
        return true
    } else {
        // Remove favorite record
        await db.favoriteComedian.deleteMany({
            where: {
                comedianId: comedianUuid,
                profileId: profileId
            }
        });
        return false
    }
}
