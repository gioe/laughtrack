import { discoverClubImageCandidates } from "@/lib/admin/clubImageDiscovery";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        clubId: z.number().int().positive(),
    })
    .strict();

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const club = await db.club.findUnique({
        where: { id: parsed.data.clubId },
        select: {
            id: true,
            name: true,
            website: true,
        },
    });

    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    try {
        const discovery = await discoverClubImageCandidates({
            clubName: club.name,
            website: club.website,
            websiteScrapingUrl: null,
        });

        return NextResponse.json({
            ok: true,
            clubId: club.id,
            ...discovery,
        });
    } catch (error) {
        console.error("Admin club image discovery failed:", error);
        return NextResponse.json(
            { error: "Image discovery failed" },
            { status: 500 },
        );
    }
}
