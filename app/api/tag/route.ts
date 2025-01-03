import { NextResponse } from "next/server";
import { getDB } from '../../../database'
import { TagDataDTO } from "../../../objects/interface/filter.interface";
const { database } = getDB();

export interface GetTagsResponse {
    containers: TagDataDTO[]
}

export async function GET() {
    return database.queries.getTags()
        .then((containers: TagDataDTO[]) => NextResponse.json({ containers }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
