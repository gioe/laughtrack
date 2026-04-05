import { auth } from "@/auth";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { z } from "zod";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

const PAGE_SIZE = 100;

const querySchema = z.object({
    userId: z.string().min(1),
    page: z.coerce.number().int().min(0).default(0),
});

export async function GET(req: NextRequest) {
    try {
        const session = await auth();
        // Bucket by profile when available; users with a session but no profile
        // row are intentionally treated as anonymous for rate limiting.
        const isAuthenticated = !!session?.profile;

        const rateLimitKey = isAuthenticated
            ? `favorites:auth:${session!.profile!.userid}`
            : `favorites:anon:${getClientIp(req)}`;
        const rl = await checkRateLimit(
            rateLimitKey,
            isAuthenticated
                ? RATE_LIMITS.authenticated
                : RATE_LIMITS.unauthenticated,
        );
        if (!rl.allowed) {
            return rateLimitResponse(rl);
        }

        if (!session) {
            return new NextResponse(null, {
                status: 401,
                headers: rateLimitHeaders(rl),
            });
        }
        if (!session.profile) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422, headers: rateLimitHeaders(rl) },
            );
        }

        const { searchParams } = new URL(req.url);
        const parsed = querySchema.safeParse({
            userId: searchParams.get("userId"),
            page: searchParams.get("page") ?? undefined,
        });

        if (!parsed.success) {
            return NextResponse.json(
                { error: "userId is required and must be a non-empty string" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const { userId, page } = parsed.data;

        if (session.profile.userid !== userId) {
            return new NextResponse(null, {
                status: 403,
                headers: rateLimitHeaders(rl),
            });
        }

        const where = { user: { userid: userId } };

        const [favorites, total] = await Promise.all([
            db.favoriteComedian.findMany({
                where,
                skip: page * PAGE_SIZE,
                take: PAGE_SIZE,
                select: {
                    comedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            instagramAccount: true,
                            instagramFollowers: true,
                            tiktokAccount: true,
                            tiktokFollowers: true,
                            youtubeAccount: true,
                            youtubeFollowers: true,
                            website: true,
                            popularity: true,
                            linktree: true,
                            hasImage: true,
                        },
                    },
                },
            }),
            db.favoriteComedian.count({ where }),
        ]);

        const comedians = favorites.map((favorite) => ({
            ...favorite.comedian,
            imageUrl: buildComedianImageUrl(
                favorite.comedian.name,
                favorite.comedian.hasImage,
            ),
            isFavorite: true,
            social_data: {
                id: favorite.comedian.id,
                instagram_account: favorite.comedian.instagramAccount,
                instagram_followers: favorite.comedian.instagramFollowers,
                tiktok_account: favorite.comedian.tiktokAccount,
                tiktok_followers: favorite.comedian.tiktokFollowers,
                youtube_account: favorite.comedian.youtubeAccount,
                youtube_followers: favorite.comedian.youtubeFollowers,
                website: favorite.comedian.website,
                popularity: favorite.comedian.popularity,
                linktree: favorite.comedian.linktree,
            },
        }));

        return NextResponse.json(
            { comedians, total },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("Error fetching favorite comedians:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorite comedians" },
            { status: 500 },
        );
    }
}
