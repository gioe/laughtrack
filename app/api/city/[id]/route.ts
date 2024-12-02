import { NextRequest, NextResponse } from "next/server";
import { Club } from "../../../../objects/class/club/Club";
import { getDB } from "../../../../database";
const { database } = getDB()

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ name: string }> }
) {
    const cityId = await params

    return database.queries.getClubsInCity(cityId)
        .then((clubs: Club[]) => NextResponse.json({ clubs }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
