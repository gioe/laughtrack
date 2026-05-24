import {
    ComedianImageDownloadError,
    HERO_HEIGHT,
    HERO_WIDTH,
    downloadComedianImage,
    generateComedianImageVariants,
    validateComedianImageAspectRatios,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        comedianId: z.number().int().positive(),
        imageUrl: z.string().url().max(2048),
        heroImageUrl: z.string().url().max(2048).optional(),
        sourcePageUrl: z.string().url().max(2048).optional(),
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

    const comedian = await db.comedian.findUnique({
        where: { id: parsed.data.comedianId },
        select: { id: true },
    });
    if (!comedian) {
        return NextResponse.json(
            { error: "Comedian not found" },
            { status: 404 },
        );
    }

    try {
        const downloaded = await downloadComedianImage(parsed.data.imageUrl);
        const heroDownloaded = parsed.data.heroImageUrl
            ? await downloadComedianImage(parsed.data.heroImageUrl)
            : downloaded;
        validateComedianImageAspectRatios({
            headshot: downloaded,
            ...(parsed.data.heroImageUrl ? { hero: heroDownloaded } : {}),
        });
        const variants = await generateComedianImageVariants(downloaded);
        const heroVariants = parsed.data.heroImageUrl
            ? await generateComedianImageVariants(heroDownloaded)
            : variants;

        const warnings: string[] = [];
        if (
            heroDownloaded.width < HERO_WIDTH ||
            heroDownloaded.height < HERO_HEIGHT
        ) {
            warnings.push(
                `Hero source ${heroDownloaded.width}x${heroDownloaded.height} is below preferred hero ${HERO_WIDTH}x${HERO_HEIGHT}; hero crop may be lower quality`,
            );
        }

        return NextResponse.json({
            ok: true,
            comedianId: comedian.id,
            source: {
                imageUrl: downloaded.sourceUrl,
                ...(heroDownloaded.sourceUrl === downloaded.sourceUrl
                    ? {}
                    : { heroImageUrl: heroDownloaded.sourceUrl }),
                sourcePageUrl: parsed.data.sourcePageUrl ?? null,
                mimeType: downloaded.mimeType,
                width: downloaded.width,
                height: downloaded.height,
            },
            avatarDataUrl: `data:image/jpeg;base64,${variants.avatarBuffer.toString("base64")}`,
            heroDataUrl: `data:image/jpeg;base64,${heroVariants.heroBuffer.toString("base64")}`,
            warnings,
        });
    } catch (error) {
        if (error instanceof ComedianImageDownloadError) {
            return NextResponse.json(
                { error: error.message, code: error.code },
                { status: 400 },
            );
        }
        console.error("Admin comedian image preview failed:", error);
        return NextResponse.json(
            { error: "Preview generation failed" },
            { status: 500 },
        );
    }
}
