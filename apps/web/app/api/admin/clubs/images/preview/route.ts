import {
    ComedianImageDownloadError,
    HERO_HEIGHT,
    HERO_WIDTH,
    downloadComedianImage,
    generateClubImageVariants,
    validateClubImageAspectRatios,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        clubId: z.number().int().positive(),
        iconImageUrl: z.string().url().max(2048),
        heroImageUrl: z.string().url().max(2048),
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
        select: { id: true },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    try {
        const icon = await downloadComedianImage(parsed.data.iconImageUrl);
        const hero = await downloadComedianImage(parsed.data.heroImageUrl);
        validateClubImageAspectRatios({ icon, hero });
        const variants = await generateClubImageVariants({ icon, hero });

        const warnings: string[] = [];
        if (hero.width < HERO_WIDTH || hero.height < HERO_HEIGHT) {
            warnings.push(
                `Hero source ${hero.width}x${hero.height} is below preferred hero ${HERO_WIDTH}x${HERO_HEIGHT}; hero crop may be lower quality`,
            );
        }

        return NextResponse.json({
            ok: true,
            clubId: club.id,
            source: {
                iconImageUrl: icon.sourceUrl,
                heroImageUrl: hero.sourceUrl,
                iconMimeType: icon.mimeType,
                heroMimeType: hero.mimeType,
                iconWidth: icon.width,
                iconHeight: icon.height,
                heroWidth: hero.width,
                heroHeight: hero.height,
            },
            iconDataUrl: `data:image/png;base64,${variants.iconBuffer.toString("base64")}`,
            heroDataUrl: `data:image/jpeg;base64,${variants.heroBuffer.toString("base64")}`,
            warnings,
        });
    } catch (error) {
        if (error instanceof ComedianImageDownloadError) {
            return NextResponse.json(
                { error: error.message, code: error.code },
                { status: 400 },
            );
        }
        console.error("Admin club image preview failed:", error);
        return NextResponse.json(
            { error: "Preview generation failed" },
            { status: 500 },
        );
    }
}
