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

export async function POST(req: NextRequest) {
    try {
        const profileId = await getProfileId(req);
        if (!profileId) {
            return new NextResponse(null, { status: 401 });
        }

        const body = await req.json();
        const comedianId = body?.comedianId;
        if (!comedianId || typeof comedianId !== "string") {
            return NextResponse.json({ error: "comedianId is required" }, { status: 400 });
        }

        await db.favoriteComedian.upsert({
            where: { profileId_comedianId: { profileId, comedianId } },
            create: { profileId, comedianId },
            update: {},
        });

        return NextResponse.json({ data: { isFavorited: true } });
    } catch (error) {
        console.error("POST /api/v1/favorites error:", error);
        return NextResponse.json({ error: "Failed to add favorite" }, { status: 500 });
    }
}
