import { NextRequest, NextResponse } from "next/server";
import { getDB } from '../../../../../database'
const { db } = getDB();


export async function PUT(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const showId = (await params).id

    const json = await req.json();

    return NextResponse.json({}, { status: 200 })
}
