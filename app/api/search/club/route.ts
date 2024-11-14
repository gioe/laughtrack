import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
import { PaginatedEntityCollectionResponse } from "../../../../objects/interface";
const { db } = getDB();

export async function POST(req: NextRequest) {
    const { body } = await req.json();
    return db.clubs.getAll(body)
        .then((result: PaginatedEntityCollectionResponse) => {
            return NextResponse.json({ result: result.entities }, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ error }, { status: 500 })
        })

}
