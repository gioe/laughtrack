import { writeAdminActionAudit } from "@/lib/admin/audit";
import {
    deleteFromBunnyStorage,
    uploadToBunnyStorage,
} from "@/lib/admin/bunnyStorage";
import {
    ComedianImageDownloadError,
    downloadComedianImage,
    generateClubImageVariants,
    getMimeExtension,
    readUploadedComedianImage,
    type DownloadedComedianImage,
} from "@/lib/admin/comedianImagePipeline";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { buildClubHeroImageUrl, buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z
    .object({
        clubId: z.number().int().positive(),
        iconImageUrl: z.string().url().max(2048).optional(),
        heroImageUrl: z.string().url().max(2048).optional(),
    })
    .strict();

type ImageSlot = "icon" | "hero";

type NormalizedRequest = {
    clubId: number;
    iconImageUrl?: string;
    heroImageUrl?: string;
    iconFile?: File;
    heroFile?: File;
};

type ProcessedSlot = {
    image: DownloadedComedianImage;
};

const adminClubSelect = {
    id: true,
    name: true,
    city: true,
    state: true,
    website: true,
    hasImage: true,
    visible: true,
    status: true,
    clubType: true,
    closedAt: true,
    totalShows: true,
    chain: { select: { id: true, name: true, slug: true, website: true } },
    scrapingSources: {
        select: {
            id: true,
            platform: true,
            scraperKey: true,
            enabled: true,
            priority: true,
        },
        orderBy: [{ priority: "asc" as const }, { id: "asc" as const }],
    },
    shows: {
        select: {
            lastScrapedDate: true,
            lastScrapedBy: true,
        },
        orderBy: [
            { lastScrapedDate: "desc" as const },
            { id: "desc" as const },
        ],
        take: 1,
    },
    imageAssets: {
        where: { isActive: true },
        select: { heroPath: true },
        orderBy: { publishedAt: "desc" as const },
        take: 1,
    },
    _count: { select: { shows: true } },
};

async function readBody(req: NextRequest) {
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
                iconImageUrl: getOptionalFormString(formData, "iconImageUrl"),
                heroImageUrl: getOptionalFormString(formData, "heroImageUrl"),
                iconFile: getOptionalFormFile(formData, "iconFile"),
                heroFile: getOptionalFormFile(formData, "heroFile"),
            } satisfies NormalizedRequest,
        } as const;
    }

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return {
            error: "Invalid payload",
            issues: parsed.error.issues,
            status: 400,
        } as const;
    }
    return { data: parsed.data satisfies NormalizedRequest } as const;
}

function getSlotInputs(data: NormalizedRequest, slot: ImageSlot) {
    if (slot === "icon") {
        return { url: data.iconImageUrl, file: data.iconFile };
    }
    return { url: data.heroImageUrl, file: data.heroFile };
}

function validateRequestSlots(data: NormalizedRequest) {
    const slots: ImageSlot[] = [];
    for (const slot of ["icon", "hero"] as const) {
        const { url, file } = getSlotInputs(data, slot);
        if (url && file) {
            const article = slot === "icon" ? "an" : "a";
            return {
                error: `Provide either ${article} ${slot} URL or ${slot} file, not both`,
                slots,
            };
        }
        if (url || file) slots.push(slot);
    }
    if (slots.length === 0) {
        return { error: "Provide an icon or hero image to upload", slots };
    }
    return { slots };
}

function serializeClubForAdmin(club: {
    id: number;
    name: string;
    city: string | null;
    state: string | null;
    website: string;
    hasImage: boolean;
    visible: boolean | null;
    status: string;
    clubType: string;
    closedAt: Date | null;
    totalShows: number;
    chain: {
        id: number;
        name: string;
        slug: string;
        website: string | null;
    } | null;
    scrapingSources: Array<{
        id: number;
        platform: string;
        scraperKey: string;
        enabled: boolean;
        priority: number;
    }>;
    shows: Array<{
        lastScrapedDate: Date | null;
        lastScrapedBy: string | null;
    }>;
    imageAssets?: Array<{
        heroPath: string | null;
    }>;
    _count: { shows: number };
}) {
    const latestShow = club.shows[0] ?? null;
    const activeImageAsset = club.imageAssets?.[0] ?? null;
    return {
        id: club.id,
        name: club.name,
        city: club.city,
        state: club.state,
        website: club.website,
        hasImage: club.hasImage,
        iconUrl: buildClubImageUrl(club.name, club.hasImage),
        heroUrl: buildClubHeroImageUrl(activeImageAsset?.heroPath),
        visible: club.visible ?? true,
        status: club.status,
        clubType: club.clubType,
        closedAt: club.closedAt?.toISOString() ?? null,
        totalShows: club.totalShows,
        scrapedShowCount: club._count.shows,
        latestScrapeAt: latestShow?.lastScrapedDate?.toISOString() ?? null,
        latestScrapeBy: latestShow?.lastScrapedBy ?? null,
        scrapingSources: club.scrapingSources,
        chain: club.chain,
    };
}

function buildClubImagePaths(
    clubId: number,
    clubName: string,
    assetSlug: string,
    sourceMimeType: string,
) {
    const encodedName = encodeURIComponent(clubName);
    const base = `club-images/${clubId}/${assetSlug}`;
    return {
        original: `${base}/original.${getMimeExtension(sourceMimeType)}`,
        icon: `clubs/${encodedName}.png`,
        hero: `clubs/${encodedName}-hero.jpg`,
    };
}

export async function POST(req: NextRequest) {
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
    const data: NormalizedRequest = normalized.data;
    const slotValidation = validateRequestSlots(data);
    if (slotValidation.error) {
        return NextResponse.json(
            { error: slotValidation.error },
            { status: 400 },
        );
    }
    const slots = slotValidation.slots;

    const club = await db.club.findUnique({
        where: { id: data.clubId },
        select: { id: true, name: true, hasImage: true },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    const processed: Partial<Record<ImageSlot, ProcessedSlot>> = {};
    let variants: Awaited<ReturnType<typeof generateClubImageVariants>>;
    try {
        for (const slot of slots) {
            const { url, file } = getSlotInputs(data, slot);
            const image = file
                ? await readUploadedComedianImage(file)
                : await downloadComedianImage(url!);
            processed[slot] = { image };
        }
        const primaryImage = processed.icon?.image ?? processed.hero?.image;
        if (!primaryImage) {
            return NextResponse.json(
                { error: "Provide an icon or hero image to upload" },
                { status: 400 },
            );
        }
        variants = await generateClubImageVariants({
            icon: processed.icon?.image ?? primaryImage,
            hero: processed.hero?.image,
        });
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

    const primaryImage = processed.icon?.image ?? processed.hero?.image ?? null;
    if (!primaryImage) {
        return NextResponse.json(
            { error: "Provide an icon or hero image to upload" },
            { status: 400 },
        );
    }
    const assetSlug = crypto.randomUUID();
    const paths = buildClubImagePaths(
        club.id,
        club.name,
        assetSlug,
        primaryImage.mimeType,
    );
    const heroOriginalPath = paths.original;
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
        if (processed.icon) {
            await uploadToBunnyStorage({
                path: paths.original,
                body: processed.icon.image.buffer,
                contentType: processed.icon.image.mimeType,
            });
            uploadedPaths.push(paths.original);
            await uploadToBunnyStorage({
                path: paths.icon,
                body: variants.iconBuffer,
                contentType: "image/png",
            });
            uploadedPaths.push(paths.icon);
        }
        if (processed.hero) {
            if (!processed.icon) {
                await uploadToBunnyStorage({
                    path: heroOriginalPath,
                    body: processed.hero.image.buffer,
                    contentType: processed.hero.image.mimeType,
                });
                uploadedPaths.push(heroOriginalPath);
            }
            if (variants.heroBuffer) {
                await uploadToBunnyStorage({
                    path: paths.hero,
                    body: variants.heroBuffer,
                    contentType: "image/jpeg",
                });
                uploadedPaths.push(paths.hero);
            }
        }
    } catch (error) {
        console.error("Admin club image publish: bunny upload failed:", error);
        await cleanupUploads("partial upload");
        return NextResponse.json(
            { error: "Bunny storage upload failed" },
            { status: 502 },
        );
    }

    try {
        const updated = await db.$transaction(async (tx) => {
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
            const iconPath = processed.icon
                ? paths.icon
                : (previousAsset?.iconPath ?? null);
            const heroPath = processed.hero
                ? paths.hero
                : (previousAsset?.heroPath ?? null);
            const originalPath = processed.icon
                ? paths.original
                : heroOriginalPath;
            const createdAsset = await tx.clubImageAsset.create({
                data: {
                    clubId: club.id,
                    sourceImageUrl: primaryImage.sourceUrl,
                    originalPath,
                    iconPath,
                    heroPath,
                    mimeType: primaryImage.mimeType,
                    width: primaryImage.width,
                    height: primaryImage.height,
                    isActive: true,
                    metadata: {
                        assetSlug,
                        iconSourceImageUrl:
                            processed.icon?.image.sourceUrl ?? null,
                        heroSourceImageUrl:
                            processed.hero?.image.sourceUrl ?? null,
                        heroMimeType: processed.hero?.image.mimeType ?? null,
                        heroWidth: processed.hero?.image.width ?? null,
                        heroHeight: processed.hero?.image.height ?? null,
                        preservedIconPath: processed.icon
                            ? null
                            : (previousAsset?.iconPath ?? null),
                        preservedHeroPath: processed.hero
                            ? null
                            : (previousAsset?.heroPath ?? null),
                    } as Prisma.InputJsonValue,
                },
            });

            const after = await tx.club.update({
                where: { id: club.id },
                data: { hasImage: Boolean(iconPath) },
                select: adminClubSelect,
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "club_image.publish",
                entityType: "club",
                entityId: club.id,
                reason: null,
                before: {
                    hasImage: club.hasImage,
                    activeAsset: previousActive[0] ?? null,
                    previousAssetIds: previousActive.map((a) => a.id),
                },
                after: {
                    hasImage: Boolean(iconPath),
                    activeAsset: createdAsset,
                    iconPath,
                    heroPath,
                    originalPath,
                    iconSourceImageUrl: processed.icon?.image.sourceUrl ?? null,
                    heroSourceImageUrl: processed.hero?.image.sourceUrl ?? null,
                },
            });

            return after;
        });

        revalidateTag("club-detail-data");
        revalidateTag("club-metadata");
        revalidateTag(club.name);

        return NextResponse.json({
            ok: true,
            club: serializeClubForAdmin(updated),
        });
    } catch (error) {
        console.error("Admin club image publish: DB update failed:", error);
        await cleanupUploads("DB update failure");
        return NextResponse.json(
            { error: "Publish failed during DB update" },
            { status: 500 },
        );
    }
}
