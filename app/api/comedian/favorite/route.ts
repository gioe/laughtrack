import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../database'
const { database } = getDB();

export async function PUT(
    req: NextRequest,
) {
    const { isFavorite, comedianId } = await req.json()

    return database.actions.addFavorite({
        comedian_id: comedianId,
        is_favorite: isFavorite,
        user_id: 16
    })
        .then(() => NextResponse.json({}, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            NextResponse.json({ message: error.message }, { status: 500 })
        });
}
