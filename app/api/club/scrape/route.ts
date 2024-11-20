import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
const { database } = getDB();
import { ClubDTO } from "../../../../objects/class/club/club.interface";
import { scrapeClubs } from "../../../../jobs/scrape/club";

export async function POST(
    req: NextRequest,
) {
    const { headless, ids } = await req.json()
    const headlessBoolean = headless == 'true' ? true : false

    return database.queries.getClubsByIds(ids)
        .then((values: ClubDTO[] | null) => {
            if (values) return scrapeClubs(values, headlessBoolean)
            throw new Error(`No value returned`)
        })
        .then((message: string) => {
            return NextResponse.json({ message }, { status: 200 })
        })
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error }, { status: 500 })
        })
}
