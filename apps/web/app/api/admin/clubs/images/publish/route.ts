import { writeAdminActionAudit } from "@/lib/admin/audit";
import {
    BunnyStorageError,
    deleteFromBunnyStorage,
    uploadToBunnyStorage,
} from "@/lib/admin/bunnyStorage";
import {
    ComedianImageDownloadError,
    buildClubAssetPaths,
    downloadComedianImage,
    generateClubImageVariants,
    readUploadedComedianImage,
    validateComedianHeadshotAspectRatio,
    type DownloadedComedianImage,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { buildClubImageAssetUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        clubId: z.number().int().positive(),
        iconImageUrl: z.string().url().max(2048).optional(),
        sourcePageUrl: z.string().url().max(2048).optional(),
    })
    .strict();

type NormalizedRequest = {
    clubId: number;
    sourcePageUrl?: string;
    iconImageUrl?: string;
    iconFile?: File;
};

async function readJsonBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function getOptionalFormString(formData: FormData, key: string) {
    const value = formData.get(key);
    return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function getOptionalFormFile(formData: FormData, key: string) {
    const value = formData.get(key);
    return value instanceof File && value.size > 0 ? value : undefined;
}

async function normalizeRequest(req: NextRequest) {
    const contentType = req.headers.get("content-type") ?? "";
    if (contentType.includes("multipart/form-data")) {
        const formData = await req.formData();
        const clubId = Number(getOptionalFormString(formData, "clubId"));
        if (!Number.isInteger(clubId) || clubId <= 0) {
            return { error: "Invalid payload", status: 400 } as const;
        }
        return {
            data: {
                clubId,
                sourcePageUrl: getOptionalFormString(formData, "sourcePageUrl"),
                iconImageUrl: getOptionalFormString(formData, "iconImageUrl"),
                iconFile: getOptionalFormFile(formData, "iconFile"),
            } satisfies NormalizedRequest,
        } as const;
    }

    const parsed = requestSchema.safeParse(await readJsonBody(req));
    if (!parsed.success) {
        return {
            error: "Invalid payload",
            issues: parsed.error.issues,
            status: 400,
        } as const;
    }
    return {
        data: {
            clubId: parsed.data.clubId,
            sourcePageUrl: parsed.data.sourcePageUrl,
            iconImageUrl: parsed.data.iconImageUrl,
            iconFile: undefined,
        } satisfies NormalizedRequest,
    } as const;
}

function serializeAsset(asset: {
    id: number;
    sourceImageUrl: string;
    originalPath: string;
    iconPath: string | null;
    heroPath: string | null;
    mimeType: string | null;
    width: number | null;
    height: number | null;
}) {
    return {
        id: asset.id,
        sourceImageUrl: asset.sourceImageUrl,
        originalPath: asset.originalPath,
        iconPath: asset.iconPath,
        heroPath: asset.heroPath,
        iconUrl: asset.iconPath ? buildClubImageAssetUrl(asset.iconPath) : null,
        heroUrl: asset.heroPath ? buildClubImageAssetUrl(asset.heroPath) : null,
        mimeType: asset.mimeType,
        width: asset.width,
        height: asset.height,
    };
}

function revalidateClub(clubName: string) {
    revalidateTag("club-search-data");
    revalidateTag("club-detail-data");
    revalidateTag("club-metadata");
    revalidateTag(clubName);
}

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const normalized = await normalizeRequest(req);
    if ("error" in normalized) {
        return NextResponse.json(
            {
                error: normalized.error,
                ...("issues" in normalized
                    ? { issues: normalized.issues }
                    : {}),
            },
            { status: normalized.status },
        );
    }
    const { data } = normalized;
    if (data.iconImageUrl && data.iconFile) {
        return NextResponse.json(
            { error: "Provide either an icon URL or icon file, not both" },
            { status: 400 },
        );
    }
    if (!data.iconImageUrl && !data.iconFile) {
        return NextResponse.json(
            { error: "Provide a club thumbnail image to upload" },
            { status: 400 },
        );
    }

    const club = await db.club.findUnique({
        where: { id: data.clubId },
        select: { id: true, name: true, hasImage: true },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    let image: DownloadedComedianImage;
    try {
        image = data.iconFile
            ? await readUploadedComedianImage(data.iconFile)
            : await downloadComedianImage(data.iconImageUrl!);
        validateComedianHeadshotAspectRatio(image);
    } catch (error) {
        if (error instanceof ComedianImageDownloadError) {
            return NextResponse.json(
                { error: error.message, code: error.code },
                { status: 400 },
            );
        }
        console.error("Admin club image publish: processing failed:", error);
        return NextResponse.json(
            { error: "Image processing failed" },
            { status: 500 },
        );
    }

    const variants = await generateClubImageVariants({ icon: image });
    const assetSlug = crypto.randomUUID();
    const paths = buildClubAssetPaths(club.id, assetSlug, image.mimeType);
    const uploadedPaths: string[] = [];

    async function cleanupUploads(reason: string) {
        for (const path of uploadedPaths) {
            try {
                await deleteFromBunnyStorage(path);
            } catch (cleanupError) {
                console.error(
                    `Admin club image publish: bunny cleanup of ${path} after ${reason} failed:`,
                    cleanupError,
                );
            }
        }
    }

    try {
        await uploadToBunnyStorage({
            path: paths.original,
            body: image.buffer,
            contentType: image.mimeType,
        });
        uploadedPaths.push(paths.original);
        await uploadToBunnyStorage({
            path: paths.icon,
            body: variants.iconBuffer,
            contentType: "image/png",
        });
        uploadedPaths.push(paths.icon);
    } catch (error) {
        console.error("Admin club image publish: bunny upload failed:", error);
        await cleanupUploads("partial upload");
        const detail =
            error instanceof BunnyStorageError
                ? error.message
                : error instanceof Error
                  ? error.message
                  : "unknown error";
        return NextResponse.json(
            { error: `Bunny storage upload failed: ${detail}` },
            { status: 502 },
        );
    }

    try {
        const newAsset = await db.$transaction(async (tx) => {
            const previousActive = await tx.clubImageAsset.findMany({
                where: { clubId: club.id, isActive: true },
                select: {
                    id: true,
                    sourceImageUrl: true,
                    originalPath: true,
                    iconPath: true,
                    heroPath: true,
                    mimeType: true,
                    width: true,
                    height: true,
                },
            });

            if (previousActive.length > 0) {
                await tx.clubImageAsset.updateMany({
                    where: { clubId: club.id, isActive: true },
                    data: { isActive: false },
                });
            }

            const previousAsset = previousActive[0] ?? null;
            const created = await tx.clubImageAsset.create({
                data: {
                    clubId: club.id,
                    sourceImageUrl: image.sourceUrl,
                    originalPath: paths.original,
                    iconPath: paths.icon,
                    heroPath: previousAsset?.heroPath ?? null,
                    mimeType: image.mimeType,
                    width: image.width,
                    height: image.height,
                    isActive: true,
                    metadata: {
                        assetSlug,
                        sourcePageUrl: data.sourcePageUrl ?? null,
                        iconSourceImageUrl: image.sourceUrl,
                        preservedHeroPath: previousAsset?.heroPath ?? null,
                    } as Prisma.InputJsonValue,
                },
            });

            await tx.club.update({
                where: { id: club.id },
                data: { hasImage: true },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "club_image.publish_thumbnail",
                entityType: "club",
                entityId: club.id,
                reason: null,
                before: {
                    hasImage: club.hasImage,
                    activeAsset: previousActive[0]
                        ? serializeAsset(previousActive[0])
                        : null,
                    previousAssetIds: previousActive.map((asset) => asset.id),
                },
                after: {
                    hasImage: true,
                    activeAsset: serializeAsset(created),
                    sourcePageUrl: data.sourcePageUrl ?? null,
                    iconSourceImageUrl: image.sourceUrl,
                },
            });

            return created;
        });

        revalidateClub(club.name);

        return NextResponse.json({
            ok: true,
            clubId: club.id,
            hasImage: true,
            asset: serializeAsset(newAsset),
        });
    } catch (error) {
        console.error(
            "Admin club image publish: DB transaction failed:",
            error,
        );
        await cleanupUploads("DB transaction failure");
        return NextResponse.json(
            { error: "Publish failed during DB update" },
            { status: 500 },
        );
    }
});
