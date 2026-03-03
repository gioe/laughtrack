'use server';

import { auth } from "@/auth"
import { toggleFavorite } from "@/lib/data/favorites/toggleFavorite";

export async function favorite(setFavorite: boolean, comedianId: string) {
    const session = await auth()
        if (!session || !session?.user || !session.user.id || !session.profile || !session.profile.id) { return  }
        if (!comedianId || typeof comedianId !== 'string') { return }

        return toggleFavorite(comedianId, session.profile.id, setFavorite)
            .then(state => state)
            .catch((error: Error) => console.log(error));
}
