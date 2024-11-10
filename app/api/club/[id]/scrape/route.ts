import { NextRequest, NextResponse } from "next/server";
import { scapeClubs } from "../../../../../jobs/scrape/club";

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const clubId = (await params).id
    const data = await req.json()
    const { headless } = data

    return scapeClubs([clubId], headless)
        .then(() => {
            return NextResponse.json({}, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ message: error.message }, { status: 500 })
        });


}
