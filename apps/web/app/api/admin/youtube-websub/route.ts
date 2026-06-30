import { writeAdminActionAudit } from "@/lib/admin/audit";
import {
    getYouTubeWebSubAdminData,
    getYouTubeWebSubEvent,
} from "@/lib/admin/youtubeWebSub";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

// Singleton row id for youtube_websub_settings (schema default is 1).
const SETTINGS_ID = 1;

const settingsSchema = z
    .object({
        feedIngestionEnabled: z.boolean().optional(),
        pushDeliveryEnabled: z.boolean().optional(),
    })
    .refine(
        (value) =>
            value.feedIngestionEnabled !== undefined ||
            value.pushDeliveryEnabled !== undefined,
        { message: "At least one flag must be provided" },
    );

type SettingsWriter = Pick<Prisma.TransactionClient, "youTubeWebSubSetting"> &
    Parameters<typeof writeAdminActionAudit>[0];

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const eventIdParam = req.nextUrl.searchParams.get("eventId");
    if (eventIdParam !== null) {
        const eventId = Number(eventIdParam);
        if (!Number.isInteger(eventId) || eventId <= 0) {
            return NextResponse.json(
                { error: "Invalid eventId" },
                { status: 400 },
            );
        }
        const event = await getYouTubeWebSubEvent(eventId);
        if (!event) {
            return NextResponse.json(
                { error: "Event not found" },
                { status: 404 },
            );
        }
        return NextResponse.json({ event });
    }

    const data = await getYouTubeWebSubAdminData();
    return NextResponse.json(data);
});

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = settingsSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    try {
        const settings = await db.$transaction(async (tx: SettingsWriter) => {
            const before = await tx.youTubeWebSubSetting.findUnique({
                where: { id: SETTINGS_ID },
                select: {
                    feedIngestionEnabled: true,
                    pushDeliveryEnabled: true,
                },
            });

            const after = await tx.youTubeWebSubSetting.upsert({
                where: { id: SETTINGS_ID },
                create: { id: SETTINGS_ID, ...parsed.data },
                update: parsed.data,
                select: {
                    feedIngestionEnabled: true,
                    pushDeliveryEnabled: true,
                },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "youtube_websub_settings.update",
                entityType: "youtube_websub_settings",
                entityId: SETTINGS_ID,
                before: before ?? {},
                after,
            });

            return after;
        });

        return NextResponse.json({ ok: true, settings });
    } catch (error) {
        console.error("Admin youtube-websub settings PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});
