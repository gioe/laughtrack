import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const flagSchema = z
    .object({
        youtubeLiveFeedEnabled: z.boolean().optional(),
        youtubeLiveNotificationsEnabled: z.boolean().optional(),
    })
    .refine(
        (value) =>
            value.youtubeLiveFeedEnabled !== undefined ||
            value.youtubeLiveNotificationsEnabled !== undefined,
        { message: "At least one flag must be provided" },
    );

type ComedianFlagWriter = Pick<Prisma.TransactionClient, "comedian"> &
    Parameters<typeof writeAdminActionAudit>[0];

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export const PATCH = withRequestMetrics(async function PATCH(
    req: NextRequest,
    ctx: { params: Promise<{ uuid: string }> },
) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const { uuid } = await ctx.params;
    if (!uuid || typeof uuid !== "string") {
        return NextResponse.json(
            { error: "Invalid comedian id" },
            { status: 400 },
        );
    }

    const parsed = flagSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const flagSelect = {
        uuid: true,
        name: true,
        youtubeLiveFeedEnabled: true,
        youtubeLiveNotificationsEnabled: true,
    } as const;

    try {
        const comedian = await db.$transaction(
            async (tx: ComedianFlagWriter) => {
                const before = await tx.comedian.findUnique({
                    where: { uuid },
                    select: flagSelect,
                });
                if (!before) return null;

                const after = await tx.comedian.update({
                    where: { uuid },
                    data: parsed.data,
                    select: flagSelect,
                });

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: "youtube_websub_comedian_flags.update",
                    entityType: "comedian",
                    entityId: after.uuid,
                    before,
                    after,
                });

                return after;
            },
        );

        if (!comedian) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404 },
            );
        }

        return NextResponse.json({ ok: true, comedian });
    } catch (error) {
        console.error("Admin youtube-websub comedian PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});
