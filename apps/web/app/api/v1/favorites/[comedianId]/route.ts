import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { getProfileId } from "../_getProfileId";

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ comedianId: string }> },
) {
    try {
        const profileId = await getProfileId(req);
        if (!profileId) {
            return new NextResponse(null, { status: 401 });
        }

        const { comedianId } = await params;

        await db.favoriteComedian.delete({
            where: { profileId_comedianId: { profileId, comedianId } },
        });

        return NextResponse.json({ data: { isFavorited: false } });
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2025") {
            return NextResponse.json({ error: "Favorite not found" }, { status: 404 });
        }
        console.error("DELETE /api/v1/favorites/[comedianId] error:", error);
        return NextResponse.json({ error: "Failed to remove favorite" }, { status: 500 });
    }
}
