import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../database'
import { EntityType } from "../../../objects/enum";
import { TagData } from "../../../objects/class/tag/Tag";
const { database } = getDB();

export async function POST(
    req: NextRequest
) {
    const { type } = await req.json()

    return database.queries.getTags(type as EntityType)
        .then((tagData: TagData[]) => NextResponse.json({ tagData }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
