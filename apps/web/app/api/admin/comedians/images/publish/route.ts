import { writeAdminActionAudit } from "@/lib/admin/audit";
import { uploadToBunnyStorage } from "@/lib/admin/bunnyStorage";
import {
    ComedianImageDownloadError,
    buildComedianAssetPaths,
    downloadComedianImage,
    generateComedianImageVariants,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        comedianId: z.number().int().positive(),
        imageUrl: z.string().url().max(2048),
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

function serializeAsset(asset: {
    id: number;
    sourceImageUrl: string;
    originalPath: string;
    avatarPath: string;
    heroPath: string;
    mimeType: string | null;
    width: number | null;
    height: number | null;
}) {
    return {
        id: asset.id,
        sourceImageUrl: asset.sourceImageUrl,
        originalPath: asset.originalPath,
        avatarPath: asset.avatarPath,
        heroPath: asset.heroPath,
        mimeType: asset.mimeType,
        width: asset.width,
        height: asset.height,
    };
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const comedian = await db.comedian.findUnique({
        where: { id: parsed.data.comedianId },
        select: { id: true, name: true, hasImage: true },
    });
    if (!comedian) {
        return NextResponse.json(
            { error: "Comedian not found" },
            { status: 404 },
        );
    }

    let downloaded;
    let variants;
    try {
        downloaded = await downloadComedianImage(parsed.data.imageUrl);
        variants = await generateComedianImageVariants(downloaded);
    } catch (error) {
        if (error instanceof ComedianImageDownloadError) {
            return NextResponse.json(
                { error: error.message, code: error.code },
                { status: 400 },
            );
        }
        console.error(
            "Admin comedian image publish: download/process failed:",
            error,
        );
        return NextResponse.json(
            { error: "Image processing failed" },
            { status: 500 },
        );
    }

    const assetSlug = crypto.randomUUID();
    const paths = buildComedianAssetPaths(
        comedian.id,
        assetSlug,
        downloaded.mimeType,
    );

    try {
        await uploadToBunnyStorage({
            path: paths.original,
            body: downloaded.buffer,
            contentType: downloaded.mimeType,
        });
        await uploadToBunnyStorage({
            path: paths.avatar,
            body: variants.avatarBuffer,
            contentType: "image/jpeg",
        });
        await uploadToBunnyStorage({
            path: paths.hero,
            body: variants.heroBuffer,
            contentType: "image/jpeg",
        });
    } catch (error) {
        console.error(
            "Admin comedian image publish: bunny upload failed:",
            error,
        );
        return NextResponse.json(
            { error: "Bunny storage upload failed" },
            { status: 502 },
        );
    }

    try {
        const newAsset = await db.$transaction(async (tx) => {
            const previousActive = await tx.comedianImageAsset.findMany({
                where: { comedianId: comedian.id, isActive: true },
                select: {
                    id: true,
                    sourceImageUrl: true,
                    originalPath: true,
                    avatarPath: true,
                    heroPath: true,
                    mimeType: true,
                    width: true,
                    height: true,
                },
            });

            if (previousActive.length > 0) {
                await tx.comedianImageAsset.updateMany({
                    where: { comedianId: comedian.id, isActive: true },
                    data: { isActive: false },
                });
            }

            const created = await tx.comedianImageAsset.create({
                data: {
                    comedianId: comedian.id,
                    sourceImageUrl: downloaded.sourceUrl,
                    originalPath: paths.original,
                    avatarPath: paths.avatar,
                    heroPath: paths.hero,
                    mimeType: downloaded.mimeType,
                    width: downloaded.width,
                    height: downloaded.height,
                    isActive: true,
                    metadata: {
                        assetSlug,
                        sourcePageUrl: parsed.data.sourcePageUrl ?? null,
                    } as Prisma.InputJsonValue,
                },
            });

            await tx.comedian.update({
                where: { id: comedian.id },
                data: { hasImage: true },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "comedian_image.publish",
                entityType: "comedian",
                entityId: comedian.id,
                reason: null,
                before: {
                    hasImage: comedian.hasImage,
                    activeAsset: previousActive[0]
                        ? serializeAsset(previousActive[0])
                        : null,
                    previousAssetIds: previousActive.map((a) => a.id),
                },
                after: {
                    hasImage: true,
                    activeAsset: serializeAsset(created),
                    sourcePageUrl: parsed.data.sourcePageUrl ?? null,
                },
            });

            return created;
        });

        revalidateTag("comedian-search-data");
        revalidateTag("comedian-detail-data");
        revalidateTag("comedian-metadata");
        revalidateTag(comedian.name);

        return NextResponse.json({
            ok: true,
            comedianId: comedian.id,
            asset: serializeAsset(newAsset),
        });
    } catch (error) {
        console.error(
            "Admin comedian image publish: DB transaction failed:",
            error,
        );
        return NextResponse.json(
            { error: "Publish failed during DB update" },
            { status: 500 },
        );
    }
}
