import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { NO_STORE_CACHE_CONTROL } from "@/lib/httpCache";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { buildComedianImageUrls } from "@/lib/data/comedian/imageAssets";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { Prisma } from "@prisma/client";

type FavoriteShowCountRow = {
    favorite_id: number;
    show_count: bigint | number;
};

async function findCanonicalShowCounts(
    comedianIds: number[],
): Promise<Map<number, number>> {
    if (comedianIds.length === 0) return new Map();

    const rows = await db.$queryRaw<FavoriteShowCountRow[]>(Prisma.sql`
        WITH RECURSIVE favorite_ancestors AS (
            SELECT
                seed.id AS favorite_id,
                seed.id AS comedian_id,
                seed.parent_comedian_id
            FROM comedians seed
            WHERE seed.id IN (${Prisma.join(comedianIds)})
              AND seed.visible = true

            UNION

            SELECT
                ancestors.favorite_id,
                parent.id AS comedian_id,
                parent.parent_comedian_id
            FROM favorite_ancestors ancestors
            JOIN comedians parent ON parent.id = ancestors.parent_comedian_id
        ),
        favorite_roots AS (
            SELECT DISTINCT
                ancestors.favorite_id,
                root.id AS root_id
            FROM favorite_ancestors ancestors
            JOIN comedians root ON root.id = ancestors.comedian_id
            WHERE ancestors.parent_comedian_id IS NULL
              AND root.visible = true
        ),
        favorite_comedian_members AS (
            SELECT
                roots.favorite_id,
                roots.root_id,
                root.id AS member_id,
                root.uuid AS member_uuid
            FROM favorite_roots roots
            JOIN comedians root ON root.id = roots.root_id

            UNION

            SELECT
                members.favorite_id,
                members.root_id,
                child.id AS member_id,
                child.uuid AS member_uuid
            FROM favorite_comedian_members members
            JOIN comedians child ON child.parent_comedian_id = members.member_id
        )
        SELECT
            members.favorite_id,
            COUNT(DISTINCT li.show_id) AS show_count
        FROM favorite_comedian_members members
        LEFT JOIN lineup_items li ON li.comedian_id = members.member_uuid
        GROUP BY members.favorite_id
    `);

    return new Map(
        rows.map((row) => [row.favorite_id, Number(row.show_count)]),
    );
}

const favoriteComedianSelect = {
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
    imageAssets: {
        where: { isActive: true },
        orderBy: { publishedAt: "desc" },
        take: 1,
        select: { avatarPath: true, heroPath: true, isActive: true },
    },
} as const;

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorites");
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

        const favorites = await db.favoriteComedian.findMany({
            where: {
                profileId: authCtx.profileId,
                comedian: { visible: true },
            },
            orderBy: { comedian: { name: "asc" } },
            select: {
                comedian: {
                    select: favoriteComedianSelect,
                },
            },
        });
        const showCounts = await findCanonicalShowCounts(
            favorites.map(({ comedian }) => comedian.id),
        );

        return NextResponse.json(
            {
                data: favorites.map(({ comedian }) => {
                    const showCount = showCounts.get(comedian.id) ?? 0;
                    return {
                        id: comedian.id,
                        uuid: comedian.uuid,
                        name: comedian.name,
                        imageUrl: buildComedianImageUrls({
                            name: comedian.name,
                            hasImage: comedian.hasImage,
                            activeAsset: comedian.imageAssets?.[0] ?? null,
                        }).imageUrl,
                        socialData: {
                            id: comedian.id,
                            instagramAccount: comedian.instagramAccount,
                            instagramFollowers: comedian.instagramFollowers,
                            tiktokAccount: comedian.tiktokAccount,
                            tiktokFollowers: comedian.tiktokFollowers,
                            youtubeAccount: comedian.youtubeAccount,
                            youtubeFollowers: comedian.youtubeFollowers,
                            website: comedian.website,
                            popularity: comedian.popularity,
                            linktree: comedian.linktree,
                        },
                        showCount,
                        isFavorite: true,
                    };
                }),
            },
            {
                headers: {
                    ...rateLimitHeaders(rl),
                    "Cache-Control": NO_STORE_CACHE_CONTROL,
                },
            },
        );
    } catch (error) {
        console.error("GET /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorites" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorites");
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
        const comedianId = (body as Record<string, unknown>)?.comedianId;
        if (!comedianId || typeof comedianId !== "string") {
            return NextResponse.json(
                { error: "comedianId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const comedian = await db.comedian.findUnique({
            where: { uuid: comedianId },
            select: { uuid: true, visible: true },
        });
        if (!comedian || !comedian.visible) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        await db.favoriteComedian.upsert({
            where: { profileId_comedianId: { profileId, comedianId } },
            create: { profileId, comedianId },
            update: {},
        });

        return NextResponse.json(
            { data: { isFavorited: true } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("POST /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
