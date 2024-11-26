import { NextResponse } from "next/server";
import { getDB } from '../../../database'
import { TagDataDTO } from "../../../objects/interface/tag.interface";
const { database } = getDB();

export async function GET() {
    console.log(`GETTING TAGS`)
    return database.queries.getTags()
        .then((containers: TagDataDTO[]) => NextResponse.json({ containers }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
