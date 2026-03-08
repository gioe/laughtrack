import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";
import { auth } from "@/auth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const session = await auth();
    const isAuthenticated = !!session?.profile;
    const rateLimitKey = isAuthenticated
        ? `clubs-id:auth:${session!.profile!.userid}`
        : `clubs-id:anon:${getClientIp(req)}`;
    const rl = checkRateLimit(
        rateLimitKey,
        isAuthenticated ? RATE_LIMITS.publicReadAuth : RATE_LIMITS.publicRead,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const { id } = await params;
    const numericId = parseInt(id, 10);

    if (isNaN(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const club = await db.club.findUnique({
            where: { id: numericId },
            select: {
                id: true,
                name: true,
                website: true,
                address: true,
                zipCode: true,
                phoneNumber: true,
            },
        });

        if (!club) {
            return NextResponse.json(
                { error: "Club not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        return NextResponse.json(
            {
                data: {
                    id: club.id,
                    name: club.name,
                    imageUrl: buildClubImageUrl(club.name),
                    website: club.website,
                    address: club.address,
                    zipCode: club.zipCode,
                    phoneNumber: club.phoneNumber,
                },
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch club" },
            { status: 500 },
        );
    }
}
