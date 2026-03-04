import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function GET(
    _req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const numericId = parseInt(id, 10);

    if (isNaN(numericId)) {
        return NextResponse.json({ error: "Invalid id" }, { status: 400 });
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
            return NextResponse.json({ error: "Club not found" }, { status: 404 });
        }

        return NextResponse.json({
            data: {
                id: club.id,
                name: club.name,
                imageUrl: buildClubImageUrl(club.name),
                website: club.website,
                address: club.address,
                zipCode: club.zipCode,
                phoneNumber: club.phoneNumber,
            },
        });
    } catch (error) {
        console.error("GET /api/v1/clubs/[id] error:", error);
        return NextResponse.json({ error: "Failed to fetch club" }, { status: 500 });
    }
}
