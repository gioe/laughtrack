import { getTags } from "@/lib/data/tags/getTags";
import { FilterDataDTO } from "@/objects/interface";
import { NextResponse } from "next/server";

export interface GetTagsResponse {
    containers: FilterDataDTO[]
}
export async function GET() {
    try {
        const containers = await getTags();
        return NextResponse.json({ containers }, { status: 200 });
    } catch (error) {
        return NextResponse.json(
            { message: error instanceof Error ? error.message : 'Unknown error occurred' },
            { status: 500 }
        );
    }
}
