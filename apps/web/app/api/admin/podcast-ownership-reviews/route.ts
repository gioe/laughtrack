import { writeAdminActionAudit } from "@/lib/admin/audit";
import { listPodcastHostshipReviews } from "@/lib/admin/podcastHostshipReviews";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

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

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function candidateSnapshot(candidate: {
    id: number;
    comedianId: number;
    podcastId: number | null;
    source: string;
    sourcePodcastId: string;
    candidateStatus: string;
    associationType: string | null;
    confidence: number;
    evidence: Prisma.JsonValue;
    reviewedAt: Date | null;
    reviewedBy: string | null;
    comedian: { id: number; name: string; uuid: string };
    podcast: { id: number; slug: string; title: string } | null;
}) {
    return {
        id: candidate.id,
        comedianId: candidate.comedianId,
        podcastId: candidate.podcastId,
        source: candidate.source,
        sourcePodcastId: candidate.sourcePodcastId,
        candidateStatus: candidate.candidateStatus,
        associationType: candidate.associationType,
        confidence: candidate.confidence,
        evidence: jsonForWrite(candidate.evidence),
        reviewedAt: candidate.reviewedAt?.toISOString() ?? null,
        reviewedBy: candidate.reviewedBy,
        comedian: candidate.comedian,
        podcast: candidate.podcast,
    };
}

function hostshipSnapshot(hostship: {
    id: number;
    comedianId: number;
    podcastId: number;
    associationType: string;
    source: string;
    reviewStatus: string;
    confidence: number;
    evidence?: Prisma.JsonValue;
    reviewedAt: Date | null;
    reviewedBy: string | null;
}) {
    return {
        id: hostship.id,
        comedianId: hostship.comedianId,
        podcastId: hostship.podcastId,
        associationType: hostship.associationType,
        source: hostship.source,
        reviewStatus: hostship.reviewStatus,
        confidence: hostship.confidence,
        evidence:
            "evidence" in hostship
                ? jsonForWrite(hostship.evidence ?? {})
                : undefined,
        reviewedAt: hostship.reviewedAt?.toISOString() ?? null,
        reviewedBy: hostship.reviewedBy,
    };
}

function jsonForWrite(value: Prisma.JsonValue): Prisma.InputJsonValue {
    return value === null ? {} : value;
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

function revalidatePodcastReviewSurfaces(slug: string | null | undefined) {
    revalidateTag("podcasts-search-page-data-v3");
    revalidateTag("podcast-detail-data-v2");
    revalidateTag("podcast-metadata");
    if (slug) {
        revalidateTag(slug);
    }
}

export async function GET() {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const candidates = await listPodcastHostshipReviews();
    return NextResponse.json({ candidates });
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = decisionSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const { podcastId, hostComedianIds, cohostComedianIds } = parsed.data;
    const selectedRoleRows = [
        ...hostComedianIds.map((comedianId) => ({
            comedianId,
            associationType: "host",
        })),
        ...cohostComedianIds.map((comedianId) => ({
            comedianId,
            associationType: "cohost",
        })),
    ] as const;
    const selectedComedianIds = selectedRoleRows.map((row) => row.comedianId);
    const denyListed = parsed.data.denyListed ?? false;
    const reason = parsed.data.reason?.trim() || null;
    if (denyListed && selectedComedianIds.length > 0) {
        return NextResponse.json(
            { error: "A deny-listed podcast cannot also have hosts" },
            { status: 400 },
        );
    }

    try {
        const result = await db.$transaction(async (tx) => {
            const podcast = await tx.podcast.findUnique({
                where: { id: podcastId },
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    source: true,
                    sourcePodcastId: true,
                    feedUrl: true,
                },
            });
            if (!podcast) return null;

            const selectedComedians = await Promise.all(
                selectedComedianIds.map((comedianId) =>
                    tx.comedian.findUnique({
                        where: { id: comedianId },
                        select: { id: true, name: true, uuid: true },
                    }),
                ),
            );
            if (selectedComedians.some((comedian) => !comedian)) {
                return { missingHost: true, podcast };
            }
            const comedianById = new Map(
                selectedComedians
                    .filter(
                        (
                            comedian,
                        ): comedian is {
                            id: number;
                            name: string;
                            uuid: string;
                        } => Boolean(comedian),
                    )
                    .map((comedian) => [comedian.id, comedian]),
            );

            const beforeCandidates = await tx.podcastCandidateReview.findMany({
                where: {
                    podcastId,
                    candidateStatus: "pending",
                },
                select: {
                    id: true,
                    comedianId: true,
                    podcastId: true,
                    source: true,
                    sourcePodcastId: true,
                    candidateStatus: true,
                    associationType: true,
                    confidence: true,
                    evidence: true,
                    reviewedAt: true,
                    reviewedBy: true,
                    comedian: {
                        select: {
                            id: true,
                            name: true,
                            uuid: true,
                        },
                    },
                    podcast: {
                        select: {
                            id: true,
                            slug: true,
                            title: true,
                        },
                    },
                },
                orderBy: [{ confidence: "desc" }, { id: "asc" }],
            });

            const beforeHostships = await tx.comedianPodcast.findMany({
                where: { podcastId },
                select: {
                    id: true,
                    comedianId: true,
                    podcastId: true,
                    source: true,
                    associationType: true,
                    reviewStatus: true,
                    confidence: true,
                    evidence: true,
                    reviewedAt: true,
                    reviewedBy: true,
                },
            });
            const beforeDenyListEntries = await tx.podcastDenyList.findMany({
                where: { podcastId, restoredAt: null },
                select: {
                    id: true,
                    podcastId: true,
                    source: true,
                    sourcePodcastId: true,
                    feedUrl: true,
                    reason: true,
                    deniedAt: true,
                    deniedBy: true,
                    restoredAt: true,
                    restoredBy: true,
                },
            });

            const reviewedAt = new Date();

            if (selectedComedianIds.length > 0) {
                for (const selectedRole of selectedRoleRows) {
                    await tx.podcastCandidateReview.updateMany({
                        where: {
                            podcastId,
                            candidateStatus: "pending",
                            comedianId: selectedRole.comedianId,
                        },
                        data: {
                            candidateStatus: "accepted",
                            associationType: selectedRole.associationType,
                            reviewedAt,
                            reviewedBy: profileId,
                        },
                    });
                }
                await tx.podcastCandidateReview.updateMany({
                    where: {
                        podcastId,
                        candidateStatus: "pending",
                        comedianId: { notIn: selectedComedianIds },
                    },
                    data: {
                        candidateStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
                await tx.comedianPodcast.updateMany({
                    where: {
                        podcastId,
                        reviewStatus: "accepted",
                        associationType: { in: ["host", "cohost"] },
                    },
                    data: {
                        reviewStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
            } else {
                await tx.podcastCandidateReview.updateMany({
                    where: {
                        podcastId,
                        candidateStatus: "pending",
                    },
                    data: {
                        candidateStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
                await tx.comedianPodcast.updateMany({
                    where: {
                        podcastId,
                        reviewStatus: "accepted",
                        associationType: { in: ["host", "cohost"] },
                    },
                    data: {
                        reviewStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
            }

            const hostships = [];
            for (const selectedRole of selectedRoleRows) {
                const hostCandidate =
                    beforeCandidates.find(
                        (candidate) =>
                            candidate.comedianId === selectedRole.comedianId,
                    ) ?? null;
                const hostSource = hostCandidate?.source ?? "manual";
                const hostConfidence = hostCandidate?.confidence ?? 1;
                const hostEvidence = hostCandidate
                    ? jsonForWrite(hostCandidate.evidence)
                    : {
                          adminAdded: true,
                          reason,
                      };
                hostships.push(
                    await tx.comedianPodcast.upsert({
                        where: {
                            comedianId_podcastId_associationType_source: {
                                comedianId: selectedRole.comedianId,
                                podcastId,
                                associationType: selectedRole.associationType,
                                source: hostSource,
                            },
                        },
                        create: {
                            comedianId: selectedRole.comedianId,
                            podcastId,
                            associationType: selectedRole.associationType,
                            source: hostSource,
                            reviewStatus: "accepted",
                            confidence: hostConfidence,
                            evidence: hostEvidence,
                            reviewedAt,
                            reviewedBy: profileId,
                        },
                        update: {
                            reviewStatus: "accepted",
                            confidence: hostConfidence,
                            evidence: hostEvidence,
                            reviewedAt,
                            reviewedBy: profileId,
                        },
                    }),
                );
            }
            const denyListEntry = denyListed
                ? await tx.podcastDenyList.upsert({
                      where: { podcastId },
                      create: {
                          podcastId,
                          source: podcast.source,
                          sourcePodcastId: podcast.sourcePodcastId,
                          feedUrl: podcast.feedUrl,
                          reason,
                          deniedAt: reviewedAt,
                          deniedBy: profileId,
                      },
                      update: {
                          source: podcast.source,
                          sourcePodcastId: podcast.sourcePodcastId,
                          feedUrl: podcast.feedUrl,
                          reason,
                          deniedAt: reviewedAt,
                          deniedBy: profileId,
                          restoredAt: null,
                          restoredBy: null,
                      },
                  })
                : null;

            if (!denyListed) {
                await tx.podcastDenyList.updateMany({
                    where: { podcastId, restoredAt: null },
                    data: {
                        restoredAt: reviewedAt,
                        restoredBy: profileId,
                    },
                });
            }

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: selectedComedianIds.length > 0
                    ? "podcast_hostship_review.approve"
                    : denyListed
                      ? "podcast_hostship_review.deny_list"
                      : "podcast_hostship_review.reject",
                entityType: "podcast",
                entityId: podcastId,
                reason,
                before: {
                    podcast,
                    candidates: beforeCandidates.map(candidateSnapshot),
                    hostships: beforeHostships.map(hostshipSnapshot),
                    denyListEntries: beforeDenyListEntries,
                },
                after: {
                    podcast,
                    hosts: hostComedianIds
                        .map((id) => comedianById.get(id))
                        .filter(
                            (
                                comedian,
                            ): comedian is {
                                id: number;
                                name: string;
                                uuid: string;
                            } => Boolean(comedian),
                        ),
                    cohosts: cohostComedianIds
                        .map((id) => comedianById.get(id))
                        .filter(
                            (
                                comedian,
                            ): comedian is {
                                id: number;
                                name: string;
                                uuid: string;
                            } => Boolean(comedian),
                        ),
                    hostships: hostships.map(hostshipSnapshot),
                    denyListEntry,
                },
            });

            return { podcast, hostships, denyListEntry };
        });

        if (!result) {
            return NextResponse.json(
                { error: "Podcast not found" },
                { status: 404 },
            );
        }
        if ("missingHost" in result) {
            return NextResponse.json(
                { error: "Host comedian not found" },
                { status: 422 },
            );
        }

        revalidatePodcastReviewSurfaces(result.podcast.slug);

        return NextResponse.json({
            ok: true,
            podcast: result.podcast,
            hostships: result.hostships,
            denyListEntry: result.denyListEntry,
        });
    } catch (error) {
        console.error("Admin podcast hostship review failed:", error);
        return NextResponse.json({ error: "Review failed" }, { status: 500 });
    }
}

export async function PUT(req: NextRequest) {
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
            const comedian = await tx.comedian.findUnique({
                where: { id: parsed.data.comedianId },
                select: { id: true, name: true, uuid: true },
            });
            if (!comedian) return null;

            const podcast = await tx.podcast.upsert({
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
                    evidence: {
                        provider: source,
                        feedUrl,
                        adminAdded: true,
                        reason,
                    },
                    sourcePayload: {
                        channelTitle: parsedFeed.title,
                        fetchedAt: new Date().toISOString(),
                    },
                    lastSyncedAt: new Date(),
                },
                update: {
                    feedUrl,
                    title: parsedFeed.title,
                    authorName: parsedFeed.authorName,
                    websiteUrl: parsedFeed.websiteUrl,
                    imageUrl: parsedFeed.imageUrl,
                    description: parsedFeed.description,
                    evidence: {
                        provider: source,
                        feedUrl,
                        adminAdded: true,
                        reason,
                    },
                    sourcePayload: {
                        channelTitle: parsedFeed.title,
                        fetchedAt: new Date().toISOString(),
                    },
                    lastSyncedAt: new Date(),
                },
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    feedUrl: true,
                },
            });

            const reviewedAt = new Date();
            await tx.comedianPodcast.upsert({
                where: {
                    comedianId_podcastId_associationType_source: {
                        comedianId: comedian.id,
                        podcastId: podcast.id,
                        associationType: "host",
                        source,
                    },
                },
                create: {
                    comedianId: comedian.id,
                    podcastId: podcast.id,
                    associationType: "host",
                    source,
                    reviewStatus: "accepted",
                    confidence: 1,
                    evidence: {
                        provider: source,
                        feedUrl,
                        adminAdded: true,
                        reason,
                    },
                    reviewedAt,
                    reviewedBy: profileId,
                },
                update: {
                    reviewStatus: "accepted",
                    confidence: 1,
                    evidence: {
                        provider: source,
                        feedUrl,
                        adminAdded: true,
                        reason,
                    },
                    reviewedAt,
                    reviewedBy: profileId,
                },
            });

            for (const episode of parsedFeed.episodes) {
                await tx.podcastEpisode.upsert({
                    where: {
                        source_sourceEpisodeId: {
                            source,
                            sourceEpisodeId: episode.sourceEpisodeId,
                        },
                    },
                    create: {
                        podcastId: podcast.id,
                        source,
                        sourceEpisodeId: episode.sourceEpisodeId,
                        guid: episode.guid,
                        title: episode.title,
                        description: episode.description,
                        releaseDate: episode.releaseDate,
                        episodeUrl: episode.episodeUrl,
                        audioUrl: episode.audioUrl,
                        externalIds: episode.guid
                            ? { rss_guid: episode.guid }
                            : {},
                        evidence: {
                            provider: source,
                            feedUrl,
                        },
                        sourcePayload: episode.sourcePayload,
                    },
                    update: {
                        podcastId: podcast.id,
                        guid: episode.guid,
                        title: episode.title,
                        description: episode.description,
                        releaseDate: episode.releaseDate,
                        episodeUrl: episode.episodeUrl,
                        audioUrl: episode.audioUrl,
                        externalIds: episode.guid
                            ? { rss_guid: episode.guid }
                            : {},
                        evidence: {
                            provider: source,
                            feedUrl,
                        },
                        sourcePayload: episode.sourcePayload,
                    },
                });
            }

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
                episodeCount: parsedFeed.episodes.length,
            };
        });

        if (!result) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404 },
            );
        }

        revalidatePodcastReviewSurfaces(result.podcast.slug);
        return NextResponse.json({ ok: true, ...result });
    } catch (error) {
        console.error("Manual RSS podcast ingest failed:", error);
        return NextResponse.json({ error: "Ingest failed" }, { status: 500 });
    }
}
