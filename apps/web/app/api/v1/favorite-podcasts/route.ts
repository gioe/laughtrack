import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const favoritePodcastSelect = {
    id: true,
    slug: true,
    title: true,
    authorName: true,
    websiteUrl: true,
    feedUrl: true,
    imageUrl: true,
    description: true,
    _count: {
        select: {
            episodes: true,
        },
    },
} as const;

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorite-podcasts");
    if (rl instanceof NextResponse) return rl;

    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422, headers: rateLimitHeaders(rl) },
            );
        }
        if (!authCtx) {
            return NextResponse.json(
                { error: "Authentication required" },
                { status: 401, headers: rateLimitHeaders(rl) },
            );
        }

        const favorites = await db.favoritePodcast.findMany({
            where: { profileId: authCtx.profileId },
            orderBy: { podcast: { title: "asc" } },
            select: {
                podcast: {
                    select: favoritePodcastSelect,
                },
            },
        });

        return NextResponse.json(
            {
                data: favorites.map(({ podcast }) => ({
                    id: podcast.id,
                    slug: podcast.slug,
                    title: podcast.title,
                    author_name: podcast.authorName,
                    website_url: podcast.websiteUrl,
                    feed_url: podcast.feedUrl,
                    image_url: podcast.imageUrl,
                    description: podcast.description,
                    episode_count: podcast._count.episodes,
                    isFavorite: true,
                })),
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/favorite-podcasts error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorite podcasts" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}

export async function POST(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorite-podcasts");
    if (rl instanceof NextResponse) return rl;

    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422, headers: rateLimitHeaders(rl) },
            );
        }
        if (!authCtx) {
            return new NextResponse(null, {
                status: 401,
                headers: rateLimitHeaders(rl),
            });
        }
        const { profileId } = authCtx;

        let body: unknown;
        try {
            body = await req.json();
        } catch {
            return NextResponse.json(
                { error: "Invalid request body" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        const rawPodcastId = (body as Record<string, unknown>)?.podcastId;
        const podcastId =
            typeof rawPodcastId === "number"
                ? rawPodcastId
                : typeof rawPodcastId === "string"
                  ? Number.parseInt(rawPodcastId, 10)
                  : NaN;
        if (!Number.isInteger(podcastId) || podcastId <= 0) {
            return NextResponse.json(
                { error: "podcastId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const podcast = await db.podcast.findUnique({
            where: { id: podcastId },
            select: { id: true },
        });
        if (!podcast) {
            return NextResponse.json(
                { error: "Podcast not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        await db.favoritePodcast.upsert({
            where: { profileId_podcastId: { profileId, podcastId } },
            create: { profileId, podcastId },
            update: {},
        });

        return NextResponse.json(
            { data: { isFavorited: true } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("POST /api/v1/favorite-podcasts error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite podcast" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
