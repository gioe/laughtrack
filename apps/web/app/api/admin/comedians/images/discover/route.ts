import { discoverComedianImageCandidates } from "@/lib/admin/comedianImageDiscovery";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const requestSchema = z
    .object({
        comedianId: z.number().int().positive(),
    })
    .strict();

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const comedian = await db.comedian.findUnique({
        where: { id: parsed.data.comedianId },
        select: {
            id: true,
            name: true,
            website: true,
            websiteScrapingUrl: true,
        },
    });

    if (!comedian) {
        return NextResponse.json(
            { error: "Comedian not found" },
            { status: 404 },
        );
    }

    try {
        const discovery = await discoverComedianImageCandidates({
            comedianName: comedian.name,
            website: comedian.website,
            websiteScrapingUrl: comedian.websiteScrapingUrl,
        });

        return NextResponse.json({
            ok: true,
            comedianId: comedian.id,
            ...discovery,
        });
    } catch (error) {
        console.error("Admin comedian image discovery failed:", error);
        return NextResponse.json(
            { error: "Image discovery failed" },
            { status: 500 },
        );
    }
});
