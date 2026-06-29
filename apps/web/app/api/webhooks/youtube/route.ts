import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const challenge = req.nextUrl.searchParams.get("hub.challenge");
    const mode = req.nextUrl.searchParams.get("hub.mode");
    const topic = req.nextUrl.searchParams.get("hub.topic");

    if (!challenge || !mode || !topic) {
        return NextResponse.json({ error: "missing_challenge" }, { status: 400 });
    }

    return new NextResponse(challenge, {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
    });
});
