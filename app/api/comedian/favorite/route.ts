import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../database'
const { database } = getDB();
import { headers } from "next/headers";

export async function PUT(
    req: NextRequest,
) {
    const headersList = await headers();
    const userId = headersList.get("user_id");

    if (!userId) {
        return NextResponse.json({ error: "Unauthenticated" }, { status: 400 });
    }

    const { isFavorite, comedianId } = await req.json()

    return database.actions.addFavorite({
        comedian_id: comedianId,
        is_favorite: isFavorite,
        user_id: Number(userId)
    })
        .then(() => NextResponse.json({
            state: !isFavorite
        }, { status: 200 }))
        .catch((error: Error) => {
            NextResponse.json({ message: error.message }, { status: 500 })
        });
}
