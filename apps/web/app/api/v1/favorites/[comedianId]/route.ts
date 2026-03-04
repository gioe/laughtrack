import { db } from "@/lib/db";
import { verifyToken } from "@/util/token";
import { NextRequest, NextResponse } from "next/server";

async function getProfileId(req: NextRequest): Promise<string | null> {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) return null;
    try {
        const decoded = verifyToken(authHeader.slice(7));
        const profile = await db.userProfile.findFirst({
            where: { user: { email: decoded.email } },
            select: { id: true },
        });
        return profile?.id ?? null;
    } catch {
        return null;
    }
}

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

        const existing = await db.favoriteComedian.findUnique({
            where: { profileId_comedianId: { profileId, comedianId } },
            select: { profileId: true },
        });

        if (!existing) {
            return NextResponse.json({ error: "Favorite not found" }, { status: 404 });
        }

        await db.favoriteComedian.delete({
            where: { profileId_comedianId: { profileId, comedianId } },
        });

        return NextResponse.json({ data: { isFavorited: false } });
    } catch (error) {
        console.error("DELETE /api/v1/favorites/[comedianId] error:", error);
        return NextResponse.json({ error: "Failed to remove favorite" }, { status: 500 });
    }
}
