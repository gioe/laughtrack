import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../database";
const { db } = getDB();

export async function GET(req: NextRequest) {
    const data = await req.json();

    return NextResponse.json({}, { status: 200 })
}
