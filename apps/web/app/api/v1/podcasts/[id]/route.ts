import { NextRequest, NextResponse } from "next/server";
import { getPodcastDetailPageDataById } from "@/lib/data/podcast/detail/getPodcastDetailPageData";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { NotFoundError } from "@/objects/NotFoundError";

const POSITIVE_INTEGER_RE = /^[1-9]\d*$/;

function parsePodcastId(raw: string): number | null {
    if (!POSITIVE_INTEGER_RE.test(raw)) return null;

    const numericId = Number(raw);
    if (!Number.isSafeInteger(numericId)) return null;

    return numericId;
}

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "podcasts-id");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = parsePodcastId(id);

    if (numericId === null) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const result = await getPodcastDetailPageDataById(numericId);
        return NextResponse.json(result, { headers: rateLimitHeaders(rl) });
    } catch (error) {
        if (error instanceof NotFoundError) {
            return NextResponse.json(
                { error: "Podcast not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        console.error("GET /api/v1/podcasts/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch podcast" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
