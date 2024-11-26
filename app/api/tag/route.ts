import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../database'
import { EntityType } from "../../../objects/enum";
import { TagDataDTO } from "../../../objects/interface/tag.interface";
const { database } = getDB();

export async function POST(
    req: NextRequest
) {
    const { type } = await req.json()

    return database.queries.getTags(type as EntityType)
        .then((containers: TagDataDTO[]) => NextResponse.json({ containers }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
