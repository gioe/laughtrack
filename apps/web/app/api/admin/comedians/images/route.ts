import { writeAdminActionAudit } from "@/lib/admin/audit";
import { deleteFromBunnyStorage } from "@/lib/admin/bunnyStorage";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const requestSchema = z
    .object({
        comedianId: z.number().int().positive(),
        slot: z.enum(["all", "thumbnail", "hero"]).default("all"),
    })
    .strict();

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
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

    const comedian = await db.comedian.findUnique({
        where: { id: parsed.data.comedianId },
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
                    avatarPath: true,
                    heroPath: true,
                },
            },
        },
    });
    if (!comedian) {
        return NextResponse.json(
            { error: "Comedian not found" },
            { status: 404 },
        );
    }

    const slot = parsed.data.slot;
    const activeAssets = comedian.imageAssets;
    const pathsToDelete = Array.from(
        new Set(
            activeAssets.flatMap((asset) => {
                if (slot === "thumbnail") return asset.avatarPath ?? [];
                if (slot === "hero") return asset.heroPath ?? [];
                return [
                    asset.originalPath,
                    asset.avatarPath,
                    asset.heroPath,
                ].filter((path): path is string => Boolean(path));
            }),
        ),
    );
    const remainingActiveAsset = (() => {
        if (slot === "all") return null;
        const firstActive = activeAssets[0] ?? null;
        if (!firstActive) return null;
        const nextAvatarPath =
            slot === "thumbnail" ? null : firstActive.avatarPath;
        const nextHeroPath = slot === "hero" ? null : firstActive.heroPath;
        if (!nextAvatarPath && !nextHeroPath) return null;
        return {
            id: firstActive.id,
            sourceImageUrl: firstActive.sourceImageUrl,
            originalPath: firstActive.originalPath,
            avatarPath: nextAvatarPath,
            heroPath: nextHeroPath,
        };
    })();
    const hasImage = Boolean(remainingActiveAsset);

    try {
        for (const path of pathsToDelete) {
            await deleteFromBunnyStorage(path);
        }

        await db.$transaction(async (tx) => {
            if (slot === "all" || !hasImage) {
                await tx.comedianImageAsset.updateMany({
                    where: { comedianId: comedian.id, isActive: true },
                    data: { isActive: false },
                });
            } else {
                await tx.comedianImageAsset.updateMany({
                    where: { comedianId: comedian.id, isActive: true },
                    data:
                        slot === "thumbnail"
                            ? { avatarPath: null }
                            : { heroPath: null },
                });
            }

            await tx.comedian.update({
                where: { id: comedian.id },
                data: { hasImage },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action:
                    slot === "thumbnail"
                        ? "comedian_image.remove_thumbnail"
                        : slot === "hero"
                          ? "comedian_image.remove_hero"
                          : "comedian_image.remove",
                entityType: "comedian",
                entityId: comedian.id,
                reason: null,
                before: {
                    hasImage: comedian.hasImage,
                    activeAssets: comedian.imageAssets,
                },
                after: {
                    hasImage,
                    activeAssets: remainingActiveAsset
                        ? [remainingActiveAsset]
                        : [],
                },
            });
        });

        revalidateTag("comedian-search-data");
        revalidateTag("comedian-detail-data");
        revalidateTag("comedian-metadata");
        revalidateTag(comedian.name);

        return NextResponse.json({
            ok: true,
            comedianId: comedian.id,
            hasImage,
            asset: remainingActiveAsset,
        });
    } catch (error) {
        console.error("Admin comedian image removal failed:", error);
        return NextResponse.json(
            { error: "Image removal failed" },
            { status: 500 },
        );
    }
});
