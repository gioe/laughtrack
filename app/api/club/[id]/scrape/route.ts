import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../../database";
const { database } = getDB();
import { queryMap } from "../../../../../database/sql";
import { ClubDTO } from "../../../../../objects/class/club/club.interface";
import { scrapeClubs } from "../../../../../jobs/scrape/club";

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const slug = await params
    const { headless } = await req.json()
    const file = queryMap.club.get.id;
    console.log(file)
    console.log(slug)

    return database.query.getClubById(slug)
        .then((value: ClubDTO[] | null) => {
            if (value) return scrapeClubs(value, headless)
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
