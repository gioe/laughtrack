import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "clubs-id");
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
        const club = await db.club.findUnique({
            where: { id: numericId, status: "active" },
            select: {
                id: true,
                name: true,
                website: true,
                address: true,
                zipCode: true,
                phoneNumber: true,
                hasImage: true,
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
                    imageUrl: buildClubImageUrl(club.name, club.hasImage),
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
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
