import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import {
    applyPublicReadRateLimit,
    rateLimitHeaders,
    type RateLimitResult,
} from "@/lib/rateLimit";
import { safePodcastImageUrl } from "@/lib/data/podcast/imageUrl";

const CACHE_CONTROL = "public, max-age=86400, s-maxage=604800";

function badRequest(rl: RateLimitResult) {
    return NextResponse.json(
        { error: "Invalid podcast artwork URL" },
        { status: 400, headers: rateLimitHeaders(rl) },
    );
}

function unsupportedMediaType(rl: RateLimitResult) {
    return NextResponse.json(
        { error: "Podcast artwork URL did not return an image" },
        { status: 415, headers: rateLimitHeaders(rl) },
    );
}

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "podcast-artwork");
    if (rl instanceof NextResponse) return rl;

    const requestedUrl = req.nextUrl.searchParams.get("url");
    const safeUrl = safePodcastImageUrl(requestedUrl);
    if (!safeUrl) return badRequest(rl);

    const matchingPodcast = await db.podcast.findFirst({
        where: { imageUrl: safeUrl },
        select: { id: true },
    });
    if (!matchingPodcast) return badRequest(rl);

    try {
        const upstream = await fetch(safeUrl, {
            headers: {
                Accept: "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
        });

        if (!upstream.ok) {
            return NextResponse.json(
                { error: "Podcast artwork fetch failed" },
                { status: upstream.status, headers: rateLimitHeaders(rl) },
            );
        }

        const contentType = upstream.headers.get("content-type") ?? "";
        if (!contentType.toLowerCase().startsWith("image/")) {
            return unsupportedMediaType(rl);
        }

        const headers = new Headers(rateLimitHeaders(rl));
        headers.set("Content-Type", contentType);
        headers.set("Cache-Control", CACHE_CONTROL);

        return new NextResponse(upstream.body, { status: 200, headers });
    } catch (error) {
        console.error("GET /api/v1/podcast-artwork error:", error);
        return NextResponse.json(
            { error: "Podcast artwork fetch failed" },
            { status: 502, headers: rateLimitHeaders(rl) },
        );
    }
}
