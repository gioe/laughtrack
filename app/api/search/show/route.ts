import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
import { EntityType } from "../../../../util/enum";
const { db } = getDB();

export async function GET(req: NextRequest) {
    const data = await req.json();

    const results = await db.search.getSearchResults(
        EntityType.Show,
        {},
    );

    return NextResponse.json({ results }, { status: 200 })
}
