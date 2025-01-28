
import { db } from "@/lib/db"

export async function toggleFavorite(comedianUuid: string,
    userId: string,
    isFavorite: boolean): Promise<boolean> {
    if (!isFavorite) {
        // Create favorite record
        await db.favoriteComedian.create({
            data: {
                comedianId: comedianUuid,
                userId: Number(userId)
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
                userId: Number(userId)
            }
        });
        return false
    }
}
