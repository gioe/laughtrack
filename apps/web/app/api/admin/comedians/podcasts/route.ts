import { writeAdminActionAudit } from "@/lib/admin/audit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const mutationSchema = z
    .object({
        comedianId: z.number().int().positive(),
        podcastId: z.number().int().positive(),
        feedUrl: z.string().trim().url().max(2000).nullable(),
    })
    .strict();

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = mutationSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const feedUrl = parsed.data.feedUrl?.trim() || null;

    try {
        const result = await db.$transaction(async (tx) => {
            const link = await tx.comedianPodcast.findFirst({
                where: {
                    comedianId: parsed.data.comedianId,
                    podcastId: parsed.data.podcastId,
                    reviewStatus: "accepted",
                },
                select: {
                    id: true,
                    associationType: true,
                    source: true,
                    reviewStatus: true,
                    confidence: true,
                    comedian: { select: { id: true, name: true } },
                    podcast: {
                        select: {
                            id: true,
                            slug: true,
                            title: true,
                            feedUrl: true,
                            websiteUrl: true,
                        },
                    },
                },
            });
            if (!link) return null;

            const updatedPodcast = await tx.podcast.update({
                where: { id: parsed.data.podcastId },
                data: { feedUrl },
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    feedUrl: true,
                    websiteUrl: true,
                },
            });

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "comedian_podcast.feed_url.update",
                entityType: "podcast",
                entityId: updatedPodcast.id,
                reason: null,
                before: {
                    comedian: link.comedian,
                    podcast: link.podcast,
                    feedUrl: link.podcast.feedUrl,
                },
                after: {
                    comedian: link.comedian,
                    podcast: updatedPodcast,
                    feedUrl,
                },
            });

            return {
                comedian: link.comedian,
                podcast: {
                    ...updatedPodcast,
                    associationType: link.associationType,
                    source: link.source,
                    reviewStatus: link.reviewStatus,
                    confidence: link.confidence,
                },
            };
        });

        if (!result) {
            return NextResponse.json(
                { error: "Comedian podcast link not found" },
                { status: 404 },
            );
        }

        revalidateTag("comedian-search-data");
        revalidateTag("comedian-detail-data");
        revalidateTag("comedian-metadata");
        revalidateTag(result.comedian.name);
        revalidateTag(result.podcast.slug);

        return NextResponse.json({ ok: true, podcast: result.podcast });
    } catch (error) {
        console.error("Admin comedian podcast RSS update failed:", error);
        return NextResponse.json(
            { error: "Podcast RSS update failed" },
            { status: 500 },
        );
    }
});
