import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'
const { db } = getDB();

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const clubId = (await params).id
    const { tagIds } = await req.json()
    const ids = JSON.parse(tagIds) as string[]
    return NextResponse.json({}, { status: 200 });
    // return db.clubs.tag(Number(clubId), ids)
    //     .then(() => NextResponse.json({}, { status: 200 }))
    //     .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
