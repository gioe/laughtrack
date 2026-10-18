import { POST as reviewHostRelationship } from "../curation/hosts/route";
import {
    resolvePodcastIntake,
    lockPodcastIntake,
    podcastEpisodesAllowed,
} from "@/lib/admin/curation/podcastIntake";
import { CurationError } from "@/lib/admin/curation/decisions";
import { writeAdminActionAudit } from "@/lib/admin/audit";
import { listPodcastHostshipReviews } from "@/lib/admin/podcastHostshipReviews";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import {
    preserveCanonicalComedianProvenance,
    resolvePodcastAttributionComedian,
} from "@/lib/data/podcast/resolvePodcastAttributionComedian";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

const decisionSchema = z
    .object({
        podcastId: z.number().int().positive(),
        hostComedianIds: z.array(z.number().int().positive()).default([]),
        cohostComedianIds: z.array(z.number().int().positive()).default([]),
        denyListed: z.boolean().optional(),
        reason: z.string().trim().max(1000).optional(),
    })
    .strict()
    .refine(
        (value) =>
            value.hostComedianIds.every(
                (id) => !value.cohostComedianIds.includes(id),
            ),
        {
            message: "A comedian cannot be both host and co-host",
            path: ["cohostComedianIds"],
        },
    );

const manualRssSchema = z
    .object({
        comedianId: z.number().int().positive(),
        feedUrl: z.string().trim().url().max(2000),
        reason: z.string().trim().max(1000).optional(),
    })
    .strict();

type RssEpisode = {
    sourceEpisodeId: string;
    guid: string | null;
    title: string;
    description: string | null;
    releaseDate: Date | null;
    episodeUrl: string | null;
    audioUrl: string | null;
    sourcePayload: Prisma.InputJsonObject;
};

type ParsedRssFeed = {
    title: string;
    authorName: string | null;
    websiteUrl: string | null;
    imageUrl: string | null;
    description: string | null;
    episodes: RssEpisode[];
};

async function readBody(req: Request) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function hashValue(value: string) {
    return crypto.createHash("sha1").update(value).digest("hex");
}

function buildPodcastSlug(
    title: string,
    source: string,
    sourcePodcastId: string,
) {
    const raw = `${title || "podcast"} ${source || ""} ${sourcePodcastId || ""}`;
    const ascii = Array.from(raw.normalize("NFKD"))
        .filter((char) => char.charCodeAt(0) < 128)
        .join("");
    return (
        ascii
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "") || "podcast"
    );
}

function decodeXmlText(value: string | null) {
    if (!value) return null;
    const text = value
        .replace(/^<!\[CDATA\[([\s\S]*)\]\]>$/m, "$1")
        .replace(/<[^>]*>/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/\s+/g, " ")
        .trim();
    return text || null;
}

function firstTag(xml: string, tag: string) {
    const match = xml.match(
        new RegExp(
            `<(?:[\\w-]+:)?${tag}\\b[^>]*>([\\s\\S]*?)</(?:[\\w-]+:)?${tag}>`,
            "i",
        ),
    );
    return decodeXmlText(match?.[1] ?? null);
}

function firstTagRaw(xml: string, tag: string) {
    const match = xml.match(
        new RegExp(
            `<(?:[\\w-]+:)?${tag}\\b[^>]*>([\\s\\S]*?)</(?:[\\w-]+:)?${tag}>`,
            "i",
        ),
    );
    return match?.[1] ?? null;
}

function firstAttr(xml: string, tag: string, attr: string) {
    const match = xml.match(
        new RegExp(
            `<(?:[\\w-]+:)?${tag}\\b[^>]*\\s${attr}=["']([^"']+)["'][^>]*>`,
            "i",
        ),
    );
    return decodeXmlText(match?.[1] ?? null);
}

function parseRssDate(value: string | null) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function parseRssFeed(xml: string, feedUrl: string): ParsedRssFeed {
    const channel = firstTagRaw(xml, "channel") ?? xml;
    const title = firstTag(channel, "title") ?? feedUrl;
    const authorName =
        firstTag(channel, "author") ?? firstTag(channel, "managingEditor");
    const websiteUrl = firstTag(channel, "link");
    const imageBlock = firstTagRaw(channel, "image");
    const imageUrl =
        firstAttr(channel, "image", "href") ??
        (imageBlock ? firstTag(imageBlock, "url") : null);
    const description =
        firstTag(channel, "description") ?? firstTag(channel, "summary");
    const itemMatches = Array.from(
        channel.matchAll(/<item\b[^>]*>([\s\S]*?)<\/item>/gi),
    );
    const episodes = itemMatches
        .map((match): RssEpisode | null => {
            const item = match[1];
            const episodeTitle = firstTag(item, "title");
            if (!episodeTitle) return null;
            const guid = firstTag(item, "guid");
            const episodeUrl = firstTag(item, "link");
            const audioUrl = firstAttr(item, "enclosure", "url");
            const sourceSeed = guid ?? episodeUrl ?? audioUrl ?? episodeTitle;
            return {
                sourceEpisodeId: guid
                    ? `guid:${guid}`
                    : `url:${hashValue(sourceSeed)}`,
                guid,
                title: episodeTitle,
                description:
                    firstTag(item, "description") ?? firstTag(item, "summary"),
                releaseDate: parseRssDate(firstTag(item, "pubDate")),
                episodeUrl,
                audioUrl,
                sourcePayload: {
                    title: episodeTitle,
                    guid,
                    link: episodeUrl,
                    enclosureUrl: audioUrl,
                    pubDate: firstTag(item, "pubDate"),
                },
            };
        })
        .filter((episode): episode is RssEpisode => Boolean(episode))
        .slice(0, 100);

    return { title, authorName, websiteUrl, imageUrl, description, episodes };
}

type ManualRssEpisodeWriter = Pick<Prisma.TransactionClient, "$queryRaw">;

async function upsertManualRssEpisode(
    tx: ManualRssEpisodeWriter,
    podcastId: number,
    feedUrl: string,
    episode: RssEpisode,
) {
    const source = "manual_rss";
    const externalIds = episode.guid ? { rss_guid: episode.guid } : {};
    const evidence = { provider: source, feedUrl };
    const rows = await tx.$queryRaw<{ id: number }[]>(Prisma.sql`
        WITH existing AS (
            SELECT
                id,
                source = ${source} AS same_source,
                CASE
                    WHEN source = ${source}
                        AND source_episode_id = ${episode.sourceEpisodeId}
                    THEN 0
                    WHEN ${episode.guid}::text IS NOT NULL
                        AND podcast_id = ${podcastId}
                        AND source = ${source}
                        AND (
                            source_episode_id = ${episode.guid}
                            OR guid = ${episode.guid}
                        )
                    THEN 1
                    ELSE 2
                END AS priority
            FROM podcast_episodes
            WHERE
                (source = ${source} AND source_episode_id = ${episode.sourceEpisodeId})
                OR (
                    ${episode.guid}::text IS NOT NULL
                    AND podcast_id = ${podcastId}
                    AND source = ${source}
                    AND (
                        source_episode_id = ${episode.guid}
                        OR guid = ${episode.guid}
                    )
                )
                OR (
                    ${episode.releaseDate}::timestamptz IS NOT NULL
                    AND podcast_id = ${podcastId}
                    AND release_date = ${episode.releaseDate}
                    AND LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                        = LOWER(REGEXP_REPLACE(BTRIM(${episode.title}), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                )
            ORDER BY priority, id
            LIMIT 1
        ),
        inserted AS (
            INSERT INTO podcast_episodes (
                podcast_id,
                source,
                source_episode_id,
                guid,
                title,
                description,
                release_date,
                episode_url,
                audio_url,
                external_ids,
                evidence,
                source_payload
            )
            SELECT
                ${podcastId},
                ${source},
                ${episode.sourceEpisodeId},
                ${episode.guid},
                ${episode.title},
                ${episode.description},
                ${episode.releaseDate},
                ${episode.episodeUrl},
                ${episode.audioUrl},
                ${JSON.stringify(externalIds)}::jsonb,
                ${JSON.stringify(evidence)}::jsonb,
                ${JSON.stringify(episode.sourcePayload)}::jsonb
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            ON CONFLICT DO NOTHING
            RETURNING id
        ),
        target AS (
            SELECT
                id,
                same_source,
                priority
            FROM existing
            UNION ALL
            SELECT
                id,
                source = ${source} AS same_source,
                CASE
                    WHEN source = ${source}
                        AND source_episode_id = ${episode.sourceEpisodeId}
                    THEN 0
                    WHEN ${episode.guid}::text IS NOT NULL
                        AND podcast_id = ${podcastId}
                        AND source = ${source}
                        AND (
                            source_episode_id = ${episode.guid}
                            OR guid = ${episode.guid}
                        )
                    THEN 1
                    ELSE 2
                END AS priority
            FROM podcast_episodes
            WHERE NOT EXISTS (SELECT 1 FROM existing)
              AND NOT EXISTS (SELECT 1 FROM inserted)
              AND (
                (source = ${source} AND source_episode_id = ${episode.sourceEpisodeId})
                OR (
                    ${episode.guid}::text IS NOT NULL
                    AND podcast_id = ${podcastId}
                    AND source = ${source}
                    AND (
                        source_episode_id = ${episode.guid}
                        OR guid = ${episode.guid}
                    )
                )
                OR (
                    ${episode.releaseDate}::timestamptz IS NOT NULL
                    AND podcast_id = ${podcastId}
                    AND release_date = ${episode.releaseDate}
                    AND LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                        = LOWER(REGEXP_REPLACE(BTRIM(${episode.title}), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                )
              )
            ORDER BY priority, id
            LIMIT 1
        ),
        updated AS (
            UPDATE podcast_episodes
            SET podcast_id = ${podcastId},
                guid = COALESCE(${episode.guid}, podcast_episodes.guid),
                title = ${episode.title},
                description = ${episode.description},
                release_date = ${episode.releaseDate},
                episode_url = ${episode.episodeUrl},
                audio_url = ${episode.audioUrl},
                external_ids = ${JSON.stringify(externalIds)}::jsonb,
                evidence = ${JSON.stringify(evidence)}::jsonb,
                source_payload = ${JSON.stringify(episode.sourcePayload)}::jsonb,
                updated_at = NOW()
            WHERE id = (SELECT id FROM target WHERE same_source)
            RETURNING id
        )
        SELECT id FROM inserted
        UNION ALL
        SELECT id FROM updated
        UNION ALL
        SELECT id FROM target
        WHERE NOT EXISTS (SELECT 1 FROM updated)
        LIMIT 1
    `);

    if (!rows[0]) {
        throw new Error(
            `Manual RSS episode could not be reconciled: ${episode.sourceEpisodeId}`,
        );
    }
}

function revalidatePodcastReviewSurfaces(slug: string | null | undefined) {
    revalidateTag("podcasts-search-page-data-v3");
    revalidateTag("podcast-detail-data-v2");
    revalidateTag("podcast-metadata");
    if (slug) {
        revalidateTag(slug);
    }
}

export const GET = withRequestMetrics(async function GET() {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const candidates = await listPodcastHostshipReviews();
    return NextResponse.json({ candidates });
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const body = await readBody(req.clone());
    if (body && typeof body === "object" && "operation" in body)
        return reviewHostRelationship(req);
    const parsed = decisionSchema.safeParse(body);
    if (!parsed.success)
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    const x = parsed.data;
    if (
        x.denyListed === undefined ||
        x.hostComedianIds.length ||
        x.cohostComedianIds.length
    )
        return NextResponse.json(
            {
                error: "Host decisions require a versioned relationship review. Refresh the Review Inbox.",
                code: "relationship_review_required",
            },
            { status: 409 },
        );
    try {
        const podcast = await db.$transaction(async (tx) => {
            await lockPodcastIntake(tx);
            const p = await tx.podcast.findUnique({
                where: { id: x.podcastId },
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    source: true,
                    sourcePodcastId: true,
                    feedUrl: true,
                },
            });
            if (!p) return null;
            const reviewedAt = new Date();
            if (x.denyListed)
                await tx.podcastDenyList.upsert({
                    where: { podcastId: p.id },
                    create: {
                        podcastId: p.id,
                        source: p.source,
                        sourcePodcastId: p.sourcePodcastId,
                        feedUrl: p.feedUrl,
                        reason: x.reason ?? null,
                        deniedAt: reviewedAt,
                        deniedBy: gate.context.profileId,
                    },
                    update: {
                        reason: x.reason ?? null,
                        deniedAt: reviewedAt,
                        deniedBy: gate.context.profileId,
                        restoredAt: null,
                        restoredBy: null,
                    },
                });
            else
                await tx.podcastDenyList.updateMany({
                    where: { podcastId: p.id, restoredAt: null },
                    data: {
                        restoredAt: reviewedAt,
                        restoredBy: gate.context.profileId,
                    },
                });
            return p;
        });
        if (!podcast)
            return NextResponse.json(
                { error: "Podcast not found" },
                { status: 404 },
            );
        revalidatePodcastReviewSurfaces(podcast.slug);
        return NextResponse.json({ ok: true, podcast });
    } catch (error) {
        console.error("Podcast entity review failed", error);
        return NextResponse.json({ error: "Review failed" }, { status: 409 });
    }
});

export const PUT = withRequestMetrics(async function PUT(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = manualRssSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const feedUrl = parsed.data.feedUrl.trim();
    if (!feedUrl.startsWith("http://") && !feedUrl.startsWith("https://")) {
        return NextResponse.json(
            { error: "Feed URL must start with http:// or https://" },
            { status: 400 },
        );
    }

    const source = "manual_rss";
    const sourcePodcastId = hashValue(feedUrl);

    const denyEntry = await db.podcastDenyList.findFirst({
        where: {
            restoredAt: null,
            OR: [{ feedUrl }, { source, sourcePodcastId }],
        },
        select: { id: true, reason: true },
    });
    if (denyEntry) {
        return NextResponse.json(
            { error: "Feed is deny-listed", reason: denyEntry.reason },
            { status: 409 },
        );
    }

    let rssText: string;
    try {
        const response = await fetch(feedUrl, {
            headers: {
                Accept: "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
                "User-Agent": "LaughTrack/1.0",
            },
        });
        if (!response.ok) {
            return NextResponse.json(
                { error: `RSS fetch failed (${response.status})` },
                { status: 422 },
            );
        }
        rssText = await response.text();
    } catch (error) {
        return NextResponse.json(
            {
                error:
                    error instanceof Error ? error.message : "RSS fetch failed",
            },
            { status: 422 },
        );
    }

    const parsedFeed = parseRssFeed(rssText, feedUrl);
    const slug = buildPodcastSlug(
        parsedFeed.title,
        source,
        sourcePodcastId.slice(0, 12),
    );
    const reason = parsed.data.reason?.trim() || null;

    try {
        const result = await db.$transaction(async (tx) => {
            const resolution = await resolvePodcastAttributionComedian(
                tx,
                parsed.data.comedianId,
            );
            if (!resolution.ok) {
                return { ineligibleComedian: true, reason: resolution.reason };
            }
            const comedian = resolution.comedian;
            const manualEvidence = preserveCanonicalComedianProvenance(
                {
                    provider: source,
                    feedUrl,
                    adminAdded: true,
                    reason,
                },
                resolution,
            );

            const existingId = await resolvePodcastIntake(tx, {
                source,
                source_podcast_id: sourcePodcastId,
                feed_url: feedUrl,
                title: parsedFeed.title,
            });
            const podcast =
                existingId !== null
                    ? await tx.podcast.findUniqueOrThrow({
                          where: { id: existingId },
                          select: {
                              id: true,
                              slug: true,
                              title: true,
                              feedUrl: true,
                          },
                      })
                    : await tx.podcast.upsert({
                          where: {
                              source_sourcePodcastId: {
                                  source,
                                  sourcePodcastId,
                              },
                          },
                          create: {
                              source,
                              sourcePodcastId,
                              slug,
                              feedUrl,
                              title: parsedFeed.title,
                              authorName: parsedFeed.authorName,
                              websiteUrl: parsedFeed.websiteUrl,
                              imageUrl: parsedFeed.imageUrl,
                              description: parsedFeed.description,
                              evidence: manualEvidence,
                              sourcePayload: {
                                  channelTitle: parsedFeed.title,
                                  fetchedAt: new Date().toISOString(),
                              },
                          },
                          update: {
                              feedUrl,
                              title: parsedFeed.title,
                              authorName: parsedFeed.authorName,
                              websiteUrl: parsedFeed.websiteUrl,
                              imageUrl: parsedFeed.imageUrl,
                              description: parsedFeed.description,
                              evidence: manualEvidence,
                              sourcePayload: {
                                  channelTitle: parsedFeed.title,
                                  fetchedAt: new Date().toISOString(),
                              },
                          },
                          select: {
                              id: true,
                              slug: true,
                              title: true,
                              feedUrl: true,
                          },
                      });

            await tx.$queryRaw(
                Prisma.sql`SELECT curation_observe_host(${parsed.data.comedianId},${podcast.id},'host',${source},${feedUrl},${JSON.stringify(manualEvidence)}::jsonb)`,
            );

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "podcast_manual_rss.ingest",
                entityType: "podcast",
                entityId: podcast.id,
                reason,
                before: {},
                after: {
                    podcast,
                    comedian,
                    feedUrl,
                    episodeCount: parsedFeed.episodes.length,
                },
            });

            return {
                podcast,
                comedian,
            };
        });

        if ("ineligibleComedian" in result) {
            return NextResponse.json(
                {
                    error: "Comedian is not eligible for podcast attribution",
                    reason: result.reason,
                },
                { status: 422 },
            );
        }

        const episodeIntakeHeld = !(await podcastEpisodesAllowed(
            result.podcast.id,
        ));
        let episodeCount = 0;
        let episodeRefreshFailed = false;
        try {
            if (!episodeIntakeHeld)
                await db.$transaction(async (tx) => {
                    for (const episode of parsedFeed.episodes) {
                        await upsertManualRssEpisode(
                            tx,
                            result.podcast.id,
                            feedUrl,
                            episode,
                        );
                    }
                    await tx.podcast.update({
                        where: { id: result.podcast.id },
                        data: { lastSyncedAt: new Date() },
                    });
                });
            episodeCount = episodeIntakeHeld ? 0 : parsedFeed.episodes.length;
        } catch (error) {
            episodeRefreshFailed = true;
            console.error(
                "Manual RSS host proposal saved, but episode refresh failed:",
                {
                    podcastId: result.podcast.id,
                    comedianId: result.comedian.id,
                    feedUrl,
                    error:
                        error instanceof Error ? error.message : String(error),
                },
            );
        }

        revalidatePodcastReviewSurfaces(result.podcast.slug);
        return NextResponse.json({
            ok: true,
            ...result,
            episodeCount,
            episodeRefreshFailed,
            episodeIntakeHeld,
            hostReviewRequired: true,
        });
    } catch (error) {
        if (error instanceof CurationError)
            return NextResponse.json(
                { error: error.message },
                { status: error.status },
            );
        console.error("Manual RSS podcast ingest failed:", error);
        return NextResponse.json({ error: "Ingest failed" }, { status: 500 });
    }
});
