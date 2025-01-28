import { toggleFavorite } from "@/lib/data/favorites/toggleFavorite";
import { headers } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function PUT(
    req: NextRequest,
) {
    try {
        const headersList = await headers();
        const userId = headersList.get("user_id");

        if (!userId) {
            return NextResponse.json({ error: "Unauthenticated" }, { status: 400 });
        }
        const { setFavorite, comedianId } = await req.json()

        return toggleFavorite(comedianId, userId, setFavorite)
            .then((state: boolean) => NextResponse.json({
                response: state
            }, { status: 200 }))
            .catch((error: Error) => {
                console.log(error)
                NextResponse.json({ message: error.message }, { status: 500 })
            });
    } catch (e) {
        console.log(e)
    }

}
