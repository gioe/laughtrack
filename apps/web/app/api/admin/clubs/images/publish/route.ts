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
    validateClubImageAspectRatios,
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
        iconImageUrl: z.string().url().max(2048),
        heroImageUrl: z.string().url().max(2048),
    })
    .strict();

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
    _count: { select: { shows: true } },
};

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
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
    _count: { shows: number };
}) {
    const latestShow = club.shows[0] ?? null;
    return {
        id: club.id,
        name: club.name,
        city: club.city,
        state: club.state,
        website: club.website,
        hasImage: club.hasImage,
        iconUrl: buildClubImageUrl(club.name, club.hasImage),
        heroUrl: buildClubHeroImageUrl(club.name, club.hasImage),
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

    const parsed = requestSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const club = await db.club.findUnique({
        where: { id: parsed.data.clubId },
        select: { id: true, name: true, hasImage: true },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    let icon;
    let hero;
    let variants;
    try {
        icon = await downloadComedianImage(parsed.data.iconImageUrl);
        hero = await downloadComedianImage(parsed.data.heroImageUrl);
        validateClubImageAspectRatios({ icon, hero });
        variants = await generateClubImageVariants({ icon, hero });
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

    const assetSlug = crypto.randomUUID();
    const paths = buildClubImagePaths(
        club.id,
        club.name,
        assetSlug,
        icon.mimeType,
    );
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
            body: icon.buffer,
            contentType: icon.mimeType,
        });
        uploadedPaths.push(paths.original);
        await uploadToBunnyStorage({
            path: paths.icon,
            body: variants.iconBuffer,
            contentType: "image/png",
        });
        uploadedPaths.push(paths.icon);
        await uploadToBunnyStorage({
            path: paths.hero,
            body: variants.heroBuffer,
            contentType: "image/jpeg",
        });
        uploadedPaths.push(paths.hero);
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

            const createdAsset = await tx.clubImageAsset.create({
                data: {
                    clubId: club.id,
                    sourceImageUrl: icon.sourceUrl,
                    originalPath: paths.original,
                    iconPath: paths.icon,
                    heroPath: paths.hero,
                    mimeType: icon.mimeType,
                    width: icon.width,
                    height: icon.height,
                    isActive: true,
                    metadata: {
                        assetSlug,
                        iconSourceImageUrl: icon.sourceUrl,
                        heroSourceImageUrl: hero.sourceUrl,
                        heroMimeType: hero.mimeType,
                        heroWidth: hero.width,
                        heroHeight: hero.height,
                    } as Prisma.InputJsonValue,
                },
            });

            const after = await tx.club.update({
                where: { id: club.id },
                data: { hasImage: true },
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
                    iconPath: paths.icon,
                    heroPath: paths.hero,
                },
                after: {
                    hasImage: true,
                    activeAsset: createdAsset,
                    iconPath: paths.icon,
                    heroPath: paths.hero,
                    originalPath: paths.original,
                    iconSourceImageUrl: icon.sourceUrl,
                    heroSourceImageUrl: hero.sourceUrl,
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
