import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'
const { db } = getDB();

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const showId = (await params).id
    const { tagIds } = await req.json()
    const ids = JSON.parse(tagIds) as string[]

    return db.shows.tag(Number(showId), ids)
        .then(() => NextResponse.json({}, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
