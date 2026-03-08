"use server";

import { auth } from "@/auth";
import { toggleFavorite } from "@/lib/data/favorites/toggleFavorite";
import { z } from "zod";

const FavoriteSchema = z.object({
    comedianId: z.string().min(1, "comedianId is required"),
    setFavorite: z.boolean(),
});

type FavoriteError = { error: string };

export async function favorite(
    setFavorite: boolean,
    comedianId: string,
): Promise<
    undefined | FavoriteError | Awaited<ReturnType<typeof toggleFavorite>>
> {
    const parsed = FavoriteSchema.safeParse({ comedianId, setFavorite });
    if (!parsed.success) {
        return { error: parsed.error.errors[0].message };
    }

    const session = await auth();
    if (
        !session ||
        !session?.user ||
        !session.user.id ||
        !session.profile ||
        !session.profile.id
    ) {
        return;
    }

    return toggleFavorite(
        parsed.data.comedianId,
        session.profile.id,
        parsed.data.setFavorite,
    )
        .then((state) => state)
        .catch((error: Error) => {
            console.error(error);
            return undefined;
        });
}
