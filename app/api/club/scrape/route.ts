import { NextRequest, NextResponse } from "next/server";
import { scrapeClubs } from "../../../../jobs/scrape/club";

export async function POST(
    req: NextRequest,
) {
    const data = await req.json()
    const { clubIds, headless } = data
    const ids = JSON.parse(clubIds) as string[]

    return scrapeClubs(ids, headless)
        .then(() => NextResponse.json({}, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
