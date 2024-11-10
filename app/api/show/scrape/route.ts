import { NextRequest, NextResponse } from "next/server";
import { scrapeShow } from "../../../../jobs/scrape/show";

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const showId = (await params).id
    const data = await req.json()
    const { headless } = data

    return scrapeShow(Number(showId), headless)
        .then(() => {
            return NextResponse.json({}, { status: 200 })
        })
        .catch((error: Error) => {
            return NextResponse.json({ message: error.message }, { status: 500 })
        });


}
