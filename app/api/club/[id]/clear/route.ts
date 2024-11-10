import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'

const { db } = getDB();
export async function PUT(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const clubId = (await params).id
    return db.shows.deleteForClub(Number(clubId))
        .then(() => {
            return NextResponse.json({}, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ error }, { status: 500 })
        });


}
