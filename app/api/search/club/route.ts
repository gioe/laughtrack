import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
import { Club } from "../../../../objects/classes/club/Club";
const { db } = getDB();

export async function POST(req: NextRequest) {
    const { body } = await req.json();
    return db.clubs.getAll(body)
        .then((results: Club[]) => {
            return NextResponse.json({ results }, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ error }, { status: 500 })
        })

}
