import { NextRequest, NextResponse } from "next/server";
import { findCoBilledComediansForComedian } from "@/lib/data/comedian/detail/findCoBilledComediansForComedian";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "comedians-id-co-bill");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = Number(id);

    if (!Number.isInteger(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const coBilledComedians = await findCoBilledComediansForComedian({
            comedianId: numericId,
        });

        return NextResponse.json(
            { data: coBilledComedians },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/[id]/co-bill error:", error);
        return NextResponse.json(
            { error: "Failed to fetch co-billed comedians" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
