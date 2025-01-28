
import { db } from "@/lib/db"

type FavoriteCreateResponse = {
    id: number;
}

type FavoriteDeleteResponse = {
    count: number;
}

export type FavoriteToggleResponse = FavoriteCreateResponse | FavoriteDeleteResponse;

export async function toggleFavorite(comedianUuid: string,
    userId: string,
    isFavorite: boolean): Promise<FavoriteToggleResponse> {
    if (!isFavorite) {
        // Create favorite record
        return db.favoriteComedian.create({
            data: {
                comedianId: comedianUuid,
                userId: Number(userId)
            },
            select: {
                id: true
            }
        });
    } else {
        // Remove favorite record
        return db.favoriteComedian.deleteMany({
            where: {
                comedianId: comedianUuid,
                userId: Number(userId)
            }
        });
    }
}
