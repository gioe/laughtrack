/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../../../../database";
const { database } = getDB();
import { ClubDTO } from "../../../../../../../objects/class/club/club.interface";
import { scrapeClubs } from "../../../../../../../jobs/scrape/club";

export async function POST(
    req: NextRequest,
) {
    const { headless, ids } = await req.json()
    const headlessBoolean = headless == 'true' ? true : false
    let task: Promise<any>;

    if (ids.length == 0) {
        task = database.queries.getAllClubs()
    } else if (ids.length == 1) {
        const name = decodeURI(ids[0])
        task = database.queries.getClubByName(name)
    } else {
        task = database.queries.getClubsByIds(ids)
    }

    return task
        .then((values: ClubDTO[] | null) => {
            if (values) return scrapeClubs(values, headlessBoolean)
            throw new Error(`No value returned`)
        })
        .then((message: string) => NextResponse.json({ message }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error }, { status: 500 }))
}
