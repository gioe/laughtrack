import { writeAdminActionAudit } from "@/lib/admin/audit";
import { deleteFromBunnyStorage } from "@/lib/admin/bunnyStorage";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { buildClubImageAssetUrl } from "@/util/imageUtil";
import { revalidateTag } from "next/cache";
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

function serializeAsset(asset: {
    id: number;
    sourceImageUrl: string;
    originalPath: string;
    iconPath: string | null;
    heroPath: string | null;
}) {
    return {
        id: asset.id,
        sourceImageUrl: asset.sourceImageUrl,
        originalPath: asset.originalPath,
        iconPath: asset.iconPath,
        heroPath: asset.heroPath,
        iconUrl: asset.iconPath ? buildClubImageAssetUrl(asset.iconPath) : null,
        heroUrl: asset.heroPath ? buildClubImageAssetUrl(asset.heroPath) : null,
    };
}

function revalidateClub(clubName: string) {
    revalidateTag("club-search-data");
    revalidateTag("club-detail-data");
    revalidateTag("club-metadata");
    revalidateTag(clubName);
}

export const DELETE = withRequestMetrics(async function DELETE(
    req: NextRequest,
) {
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
        select: {
            id: true,
            name: true,
            hasImage: true,
            imageAssets: {
                where: { isActive: true },
                select: {
                    id: true,
                    sourceImageUrl: true,
                    originalPath: true,
                    iconPath: true,
                    heroPath: true,
                },
            },
        },
    });
    if (!club) {
        return NextResponse.json({ error: "Club not found" }, { status: 404 });
    }

    const activeAssets = club.imageAssets;
    const pathsToDelete = Array.from(
        new Set(
            activeAssets
                .map((asset) => asset.iconPath)
                .filter((path): path is string => Boolean(path)),
        ),
    );
    const firstActive = activeAssets[0] ?? null;
    const remainingActiveAsset =
        firstActive?.heroPath && firstActive
            ? {
                  id: firstActive.id,
                  sourceImageUrl: firstActive.sourceImageUrl,
                  originalPath: firstActive.originalPath,
                  iconPath: null,
                  heroPath: firstActive.heroPath,
              }
            : null;

    try {
        for (const path of pathsToDelete) {
            await deleteFromBunnyStorage(path);
        }

        await db.$transaction(async (tx) => {
            if (remainingActiveAsset) {
                await tx.clubImageAsset.updateMany({
                    where: { clubId: club.id, isActive: true },
                    data: { iconPath: null },
                });
            } else {
                await tx.clubImageAsset.updateMany({
                    where: { clubId: club.id, isActive: true },
                    data: { isActive: false },
                });
            }

            await tx.club.update({
                where: { id: club.id },
                data: { hasImage: false },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "club_image.remove_thumbnail",
                entityType: "club",
                entityId: club.id,
                reason: null,
                before: {
                    hasImage: club.hasImage,
                    activeAssets: club.imageAssets.map(serializeAsset),
                },
                after: {
                    hasImage: false,
                    activeAssets: remainingActiveAsset
                        ? [serializeAsset(remainingActiveAsset)]
                        : [],
                },
            });
        });

        revalidateClub(club.name);

        return NextResponse.json({
            ok: true,
            clubId: club.id,
            hasImage: false,
            asset: remainingActiveAsset
                ? serializeAsset(remainingActiveAsset)
                : null,
        });
    } catch (error) {
        console.error("Admin club image removal failed:", error);
        return NextResponse.json(
            { error: "Image removal failed" },
            { status: 500 },
        );
    }
});
