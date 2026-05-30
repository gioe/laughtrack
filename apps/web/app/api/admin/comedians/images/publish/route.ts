import { writeAdminActionAudit } from "@/lib/admin/audit";
import {
    deleteFromBunnyStorage,
    uploadToBunnyStorage,
} from "@/lib/admin/bunnyStorage";
import {
    ComedianImageDownloadError,
    buildComedianAssetPaths,
    downloadComedianImage,
    generateComedianImageVariants,
    getMimeExtension,
    readUploadedComedianImage,
    validateComedianHeadshotAspectRatio,
    validateComedianHeroAspectRatio,
    type DownloadedComedianImage,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { buildComedianImageAssetUrl } from "@/lib/data/comedian/imageAssets";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const requestSchema = z
    .object({
        comedianId: z.number().int().positive(),
        imageUrl: z.string().url().max(2048).optional(),
        headshotImageUrl: z.string().url().max(2048).optional(),
        heroImageUrl: z.string().url().max(2048).optional(),
        sourcePageUrl: z.string().url().max(2048).optional(),
    })
    .strict();

type ImageSlot = "headshot" | "hero";

type NormalizedRequest = {
    comedianId: number;
    sourcePageUrl?: string;
    legacyCombined: boolean;
    headshotImageUrl?: string;
    heroImageUrl?: string;
    headshotFile?: File;
    heroFile?: File;
};

type ProcessedSlot = {
    image: DownloadedComedianImage;
    variants: Awaited<ReturnType<typeof generateComedianImageVariants>>;
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
        const comedianId = Number(
            getOptionalFormString(formData, "comedianId"),
        );
        if (!Number.isInteger(comedianId) || comedianId <= 0) {
            return { error: "Invalid payload", status: 400 } as const;
        }
        return {
            data: {
                comedianId,
                sourcePageUrl: getOptionalFormString(formData, "sourcePageUrl"),
                legacyCombined: false,
                headshotImageUrl: getOptionalFormString(
                    formData,
                    "headshotImageUrl",
                ),
                heroImageUrl: getOptionalFormString(formData, "heroImageUrl"),
                headshotFile: getOptionalFormFile(formData, "headshotFile"),
                heroFile: getOptionalFormFile(formData, "heroFile"),
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
            comedianId: parsed.data.comedianId,
            sourcePageUrl: parsed.data.sourcePageUrl,
            legacyCombined:
                Boolean(parsed.data.imageUrl) &&
                !parsed.data.headshotImageUrl &&
                !parsed.data.heroImageUrl,
            headshotImageUrl:
                parsed.data.headshotImageUrl ?? parsed.data.imageUrl,
            heroImageUrl: parsed.data.heroImageUrl ?? parsed.data.imageUrl,
        } satisfies NormalizedRequest,
    } as const;
}

function getSlotInputs(data: NormalizedRequest, slot: ImageSlot) {
    if (slot === "headshot") {
        return {
            url: data.headshotImageUrl,
            file: data.headshotFile,
        };
    }
    return {
        url: data.heroImageUrl,
        file: data.heroFile,
    };
}

function validateRequestSlots(data: NormalizedRequest) {
    const slots: ImageSlot[] = [];
    for (const slot of ["headshot", "hero"] as const) {
        const { url, file } = getSlotInputs(data, slot);
        if (url && file) {
            return {
                error: `Provide either a ${slot} URL or ${slot} file, not both`,
                slots,
            };
        }
        if (url || file) slots.push(slot);
    }
    if (slots.length === 0) {
        return {
            error: "Provide a headshot or hero image to upload",
            slots,
        };
    }
    return { slots };
}

function serializeAsset(asset: {
    id: number;
    sourceImageUrl: string;
    originalPath: string;
    avatarPath: string | null;
    heroPath: string | null;
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
        avatarUrl: asset.avatarPath
            ? buildComedianImageAssetUrl(asset.avatarPath)
            : null,
        heroUrl: asset.heroPath
            ? buildComedianImageAssetUrl(asset.heroPath)
            : null,
        mimeType: asset.mimeType,
        width: asset.width,
        height: asset.height,
    };
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
    const slotValidation = validateRequestSlots(data);
    if (slotValidation.error) {
        return NextResponse.json(
            { error: slotValidation.error },
            { status: 400 },
        );
    }
    const slots = slotValidation.slots;

    const comedian = await db.comedian.findUnique({
        where: { id: data.comedianId },
        select: { id: true, name: true, hasImage: true },
    });
    if (!comedian) {
        return NextResponse.json(
            { error: "Comedian not found" },
            { status: 404 },
        );
    }

    const processed: Partial<Record<ImageSlot, ProcessedSlot>> = {};
    try {
        if (data.legacyCombined && data.headshotImageUrl) {
            const image = await downloadComedianImage(data.headshotImageUrl);
            validateComedianHeadshotAspectRatio(image);
            const variants = await generateComedianImageVariants(image);
            processed.headshot = { image, variants };
            processed.hero = { image, variants };
        } else {
            for (const slot of slots) {
                const { url, file } = getSlotInputs(data, slot);
                const image = file
                    ? await readUploadedComedianImage(file)
                    : await downloadComedianImage(url!);
                if (slot === "headshot") {
                    validateComedianHeadshotAspectRatio(image);
                } else {
                    validateComedianHeroAspectRatio(image);
                }
                processed[slot] = {
                    image,
                    variants: await generateComedianImageVariants(image),
                };
            }
        }
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
    const primaryImage =
        processed.headshot?.image ?? processed.hero?.image ?? null;
    if (!primaryImage) {
        return NextResponse.json(
            { error: "Provide a headshot or hero image to upload" },
            { status: 400 },
        );
    }
    const paths = buildComedianAssetPaths(
        comedian.id,
        assetSlug,
        primaryImage.mimeType,
    );
    const heroOriginalPath =
        processed.hero &&
        processed.headshot &&
        processed.headshot.image !== processed.hero.image
            ? `comedian-images/${comedian.id}/${assetSlug}/hero-original.${getMimeExtension(
                  processed.hero.image.mimeType,
              )}`
            : paths.original;

    const uploadedPaths: string[] = [];
    async function cleanupUploads(reason: string) {
        if (uploadedPaths.length === 0) return;
        for (const path of uploadedPaths) {
            try {
                await deleteFromBunnyStorage(path);
            } catch (cleanupError) {
                console.error(
                    `Admin comedian image publish: bunny cleanup of ${path} after ${reason} failed:`,
                    cleanupError,
                );
            }
        }
    }

    try {
        if (processed.headshot) {
            await uploadToBunnyStorage({
                path: paths.original,
                body: processed.headshot.image.buffer,
                contentType: processed.headshot.image.mimeType,
            });
            uploadedPaths.push(paths.original);
            await uploadToBunnyStorage({
                path: paths.avatar,
                body: processed.headshot.variants.avatarBuffer,
                contentType: "image/jpeg",
            });
            uploadedPaths.push(paths.avatar);
        }
        if (processed.hero) {
            if (!processed.headshot || heroOriginalPath !== paths.original) {
                await uploadToBunnyStorage({
                    path: heroOriginalPath,
                    body: processed.hero.image.buffer,
                    contentType: processed.hero.image.mimeType,
                });
                uploadedPaths.push(heroOriginalPath);
            }
            await uploadToBunnyStorage({
                path: paths.hero,
                body: processed.hero.variants.heroBuffer,
                contentType: "image/jpeg",
            });
            uploadedPaths.push(paths.hero);
        }
    } catch (error) {
        console.error(
            "Admin comedian image publish: bunny upload failed:",
            error,
        );
        await cleanupUploads("partial upload");
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

            const previousAsset = previousActive[0] ?? null;
            const avatarPath = processed.headshot
                ? paths.avatar
                : (previousAsset?.avatarPath ?? null);
            const heroPath = processed.hero
                ? paths.hero
                : (previousAsset?.heroPath ?? null);
            const created = await tx.comedianImageAsset.create({
                data: {
                    comedianId: comedian.id,
                    sourceImageUrl: primaryImage.sourceUrl,
                    originalPath: processed.headshot
                        ? paths.original
                        : heroOriginalPath,
                    avatarPath,
                    heroPath,
                    mimeType: primaryImage.mimeType,
                    width: primaryImage.width,
                    height: primaryImage.height,
                    isActive: true,
                    metadata: {
                        assetSlug,
                        sourcePageUrl: data.sourcePageUrl ?? null,
                        headshotSourceImageUrl:
                            processed.headshot?.image.sourceUrl ?? null,
                        heroSourceImageUrl:
                            processed.hero?.image.sourceUrl ?? null,
                        preservedAvatarPath: processed.headshot
                            ? null
                            : (previousAsset?.avatarPath ?? null),
                        preservedHeroPath: processed.hero
                            ? null
                            : (previousAsset?.heroPath ?? null),
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
                    sourcePageUrl: data.sourcePageUrl ?? null,
                    headshotSourceImageUrl:
                        processed.headshot?.image.sourceUrl ?? null,
                    heroSourceImageUrl: processed.hero?.image.sourceUrl ?? null,
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
        await cleanupUploads("DB transaction failure");
        return NextResponse.json(
            { error: "Publish failed during DB update" },
            { status: 500 },
        );
    }
});
