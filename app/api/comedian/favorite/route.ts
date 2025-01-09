import { NextRequest, NextResponse } from "next/server";
import { db } from "../../../lib/db";
import { headers } from "next/headers";

export async function PUT(
    req: NextRequest,
) {
    try {
        const headersList = await headers();
        const userId = headersList.get("user_id");

        if (!userId) {
            return NextResponse.json({ error: "Unauthenticated" }, { status: 400 });
        }

        const { isFavorite, comedianId } = await req.json()

        return db.favoriteComedian.create({
            data: {
                comedianId: comedianId,
                userId: Number(userId)
            },
            select: {
                id: true
            }
        })
            .then(() => NextResponse.json({
                state: !isFavorite
            }, { status: 200 }))
            .catch((error: Error) => {
                NextResponse.json({ message: error.message }, { status: 500 })
            });
    } catch (e) {
        console.log(e)
    }

}
