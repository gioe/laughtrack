import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";

export async function POST(req: NextRequest) {
    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422 },
            );
        }
        if (!authCtx) {
            return new NextResponse(null, { status: 401 });
        }
        const { profileId } = authCtx;

        let body: unknown;
        try {
            body = await req.json();
        } catch {
            return NextResponse.json(
                { error: "Invalid request body" },
                { status: 400 },
            );
        }
        const comedianId = (body as Record<string, unknown>)?.comedianId;
        if (!comedianId || typeof comedianId !== "string") {
            return NextResponse.json(
                { error: "comedianId is required" },
                { status: 400 },
            );
        }

        const comedian = await db.comedian.findUnique({
            where: { uuid: comedianId },
            select: { uuid: true },
        });
        if (!comedian) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404 },
            );
        }

        await db.favoriteComedian.upsert({
            where: { profileId_comedianId: { profileId, comedianId } },
            create: { profileId, comedianId },
            update: {},
        });

        return NextResponse.json({ data: { isFavorited: true } });
    } catch (error) {
        console.error("POST /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite" },
            { status: 500 },
        );
    }
}
