/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
import { scrapeShow } from "../../../../jobs/scrape/show";
import { Show } from "../../../../objects/class/show/Show";
import { Club } from "../../../../objects/class/club/Club";
const { database } = getDB();
export async function POST(
    req: NextRequest
) {
    const { headless, ids } = await req.json()
    const headlessBoolean = headless == 'true' ? true : false
    return database.queries.getShowById(ids[0])
        .then((data: any | null) => {
            if (data) {
                const show = new Show(data.response.show)
                const club = new Club(data.response.club)
                return scrapeShow(show, club, headlessBoolean)
            }
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
