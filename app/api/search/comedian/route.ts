import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
import { EntityType } from "../../../../util/enum";
import { Comedian } from "../../../../objects/classes/comedian/Comedian";
const { db } = getDB();

export async function POST(req: NextRequest) {
    const { body } = await req.json();
    return db.search.getSearchResults(EntityType.Comedian, body)
        .then((results: Comedian[]) => {
            return NextResponse.json({ results }, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ error }, { status: 500 })
        })

}
