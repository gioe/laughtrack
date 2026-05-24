import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

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

export async function DELETE(req: NextRequest) {
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

    try {
        await db.$transaction(async (tx) => {
            await tx.comedianImageAsset.updateMany({
                where: { comedianId: comedian.id, isActive: true },
                data: { isActive: false },
            });

            await tx.comedian.update({
                where: { id: comedian.id },
                data: { hasImage: false },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "comedian_image.remove",
                entityType: "comedian",
                entityId: comedian.id,
                reason: null,
                before: {
                    hasImage: comedian.hasImage,
                    activeAssets: comedian.imageAssets,
                },
                after: {
                    hasImage: false,
                    activeAssets: [],
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
            hasImage: false,
        });
    } catch (error) {
        console.error("Admin comedian image removal failed:", error);
        return NextResponse.json(
            { error: "Image removal failed" },
            { status: 500 },
        );
    }
}
