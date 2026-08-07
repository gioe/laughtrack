import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import {
    DISCOVERY_FEATURE_VERSION,
    type DiscoveryAvailability,
} from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

const DAY_MS = 24 * 60 * 60 * 1_000;
const DEFAULT_HORIZON_DAYS = 90;
const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 50;
const NEWLY_ADDED_DAYS = 14;
const MAX_SNAPSHOT_AGE_HOURS = 48;
const MIN_CONFIDENCE = 0.5;
const MIN_MOMENTUM = 0.15;
const MIN_GROWTH = 0.6;
const MAX_EARLY_PROMINENCE = 0.6;

export type FreshAndRisingReasonKind =
    | "newly_added"
    | "starting_to_buzz"
    | "catch_them_early";

export interface AnnouncementProvenance {
    verified: boolean;
    source: string;
    announcedAt: Date;
}

export interface FreshAndRisingSignalEvidence {
    behavior: {
        momentumWindow: "recent" | "trailing28" | "insufficient";
        recentDetailActors: number;
        recentTicketIntentActors: number;
        recentDemandActors: number;
        growth: number | null;
        confidence: number;
    };
    favorites: {
        recentCount: number;
        baselineCount: number;
        growth: number | null;
        confidence: number;
    };
    social: {
        pairedSeries: number;
        observedSeries: number;
        growth: number | null;
        confidence: number;
    };
    confidenceReasons: string[];
}

export interface FreshAndRisingReasonEvidence {
    firstDiscoveredAt: Date | null;
    freshnessProvenance:
        | { kind: "laughtrack_observation" }
        | { kind: "verified_announcement"; source: string; announcedAt: Date };
    featureVersion: string | null;
    featureAsOf: Date | null;
    prominence: number | null;
    momentum: number | null;
    growth: number | null;
    confidence: number | null;
    availability: DiscoveryAvailability | null;
    signals: FreshAndRisingSignalEvidence | null;
}

export interface FreshAndRisingReason {
    kind: FreshAndRisingReasonKind;
    label: string;
    evidence: FreshAndRisingReasonEvidence;
}

export interface FreshAndRisingRailItem {
    show: ShowDTO;
    performer: {
        id: number;
        uuid: string;
        name: string;
    };
    reason: FreshAndRisingReason;
}

export interface FreshAndRisingRail {
    railKey: FreshAndRisingReasonKind;
    label: string;
    items: FreshAndRisingRailItem[];
}

export interface FreshAndRisingRails {
    newlyAdded: FreshAndRisingRail;
    startingToBuzz: FreshAndRisingRail;
    catchThemEarly: FreshAndRisingRail;
}

export interface FreshAndRisingOptions {
    now?: Date;
    horizonDays?: number;
    limit?: number;
}

export interface FreshAndRisingEvidenceRow {
    showId: number;
    showDate: Date;
    showName: string | null;
    firstDiscoveredAt: Date | null;
    clubVisible: boolean;
    performerVisible: boolean;
    canonicalVisible: boolean;
    ticketsSoldOut: boolean;
    hasPurchasePath: boolean;
    canonicalComedianId: number;
    canonicalComedianUuid: string;
    canonicalComedianName: string;
    featureVersion: string | null;
    featureAsOf: Date | null;
    prominence: number | null;
    momentum: number | null;
    growth: number | null;
    confidence: number | null;
    availability: string | null;
    featureEvidence: unknown;
    announcementProvenance?: AnnouncementProvenance | null;
}

interface ClassifiedItem {
    showId: number;
    performer: FreshAndRisingRailItem["performer"];
    reason: FreshAndRisingReason;
    score: number;
    showDate: Date;
}

interface ClassifiedRails {
    newlyAdded: ClassifiedItem[];
    startingToBuzz: ClassifiedItem[];
    catchThemEarly: ClassifiedItem[];
}

interface ClassifyOptions {
    now: Date;
    horizonDays: number;
    limit: number;
}

type FreshAndRisingQueryRow = {
    show_id: number;
    show_date: Date;
    show_name: string | null;
    first_discovered_at: Date | null;
    club_visible: boolean;
    performer_visible: boolean;
    canonical_visible: boolean;
    tickets_sold_out: boolean;
    has_purchase_path: boolean;
    canonical_comedian_id: number;
    canonical_comedian_uuid: string;
    canonical_comedian_name: string;
    feature_version: string | null;
    feature_as_of: Date | null;
    prominence: number | null;
    momentum: number | null;
    growth: number | null;
    confidence: number | null;
    availability: string | null;
    feature_evidence: unknown;
};

function record(value: unknown): Record<string, unknown> | null {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : null;
}

function finiteNumber(value: unknown, fallback = 0): number {
    return typeof value === "number" && Number.isFinite(value)
        ? value
        : fallback;
}

function nullableNumber(value: unknown): number | null {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeSignals(value: unknown): FreshAndRisingSignalEvidence | null {
    const root = record(value);
    const behavior = record(root?.behavior);
    const favorites = record(root?.favorites);
    const social = record(root?.social);
    if (!root || !behavior || !favorites || !social) return null;

    const momentumWindow = behavior.momentumWindow;
    return {
        behavior: {
            momentumWindow:
                momentumWindow === "recent" || momentumWindow === "trailing28"
                    ? momentumWindow
                    : "insufficient",
            recentDetailActors: finiteNumber(behavior.recentDetailActors),
            recentTicketIntentActors: finiteNumber(
                behavior.recentTicketIntentActors,
            ),
            recentDemandActors: finiteNumber(behavior.recentDemandActors),
            growth: nullableNumber(behavior.growth),
            confidence: finiteNumber(behavior.confidence),
        },
        favorites: {
            recentCount: finiteNumber(favorites.recentCount),
            baselineCount: finiteNumber(favorites.baselineCount),
            growth: nullableNumber(favorites.growth),
            confidence: finiteNumber(favorites.confidence),
        },
        social: {
            pairedSeries: finiteNumber(social.pairedSeries),
            observedSeries: finiteNumber(social.observedSeries),
            growth: nullableNumber(social.growth),
            confidence: finiteNumber(social.confidence),
        },
        confidenceReasons: Array.isArray(root.confidenceReasons)
            ? root.confidenceReasons.filter(
                  (reason): reason is string => typeof reason === "string",
              )
            : [],
    };
}

function validAvailability(value: string | null): DiscoveryAvailability | null {
    return value === "available" ||
        value === "unknown" ||
        value === "unavailable"
        ? value
        : null;
}

function titleSaysSoldOut(name: string | null): boolean {
    return /sold[ -]?out/i.test(name ?? "");
}

function isEligible(
    row: FreshAndRisingEvidenceRow,
    now: Date,
    horizonEnd: Date,
): boolean {
    return (
        row.clubVisible &&
        row.performerVisible &&
        row.canonicalVisible &&
        !row.ticketsSoldOut &&
        !titleSaysSoldOut(row.showName) &&
        row.hasPurchasePath &&
        row.showDate.getTime() > now.getTime() &&
        row.showDate.getTime() <= horizonEnd.getTime()
    );
}

function verifiedAnnouncement(
    row: FreshAndRisingEvidenceRow,
    now: Date,
): AnnouncementProvenance | null {
    const provenance = row.announcementProvenance;
    return provenance?.verified === true &&
        provenance.source.trim().length > 0 &&
        !Number.isNaN(provenance.announcedAt.getTime()) &&
        provenance.announcedAt.getTime() <= now.getTime()
        ? provenance
        : null;
}

function reasonEvidence(
    row: FreshAndRisingEvidenceRow,
    now: Date,
): FreshAndRisingReasonEvidence {
    const announcement = verifiedAnnouncement(row, now);
    return {
        firstDiscoveredAt: row.firstDiscoveredAt,
        freshnessProvenance: announcement
            ? {
                  kind: "verified_announcement",
                  source: announcement.source.trim(),
                  announcedAt: announcement.announcedAt,
              }
            : { kind: "laughtrack_observation" },
        featureVersion: row.featureVersion,
        featureAsOf: row.featureAsOf,
        prominence: row.prominence,
        momentum: row.momentum,
        growth: row.growth,
        confidence: row.confidence,
        availability: validAvailability(row.availability),
        signals: normalizeSignals(row.featureEvidence),
    };
}

function hasPositiveGrowthSupport(
    signals: FreshAndRisingSignalEvidence,
): boolean {
    return [signals.behavior, signals.favorites, signals.social].some(
        (channel) =>
            channel.confidence > 0 &&
            channel.growth !== null &&
            channel.growth > 0,
    );
}

function hasMomentumSupport(signals: FreshAndRisingSignalEvidence): boolean {
    return (
        signals.behavior.confidence > 0 &&
        signals.behavior.momentumWindow !== "insufficient" &&
        signals.behavior.recentDemandActors > 0
    );
}

function hasUsableSnapshot(
    row: FreshAndRisingEvidenceRow,
    now: Date,
): row is FreshAndRisingEvidenceRow & {
    featureAsOf: Date;
    prominence: number;
    momentum: number;
    growth: number;
    confidence: number;
} {
    return (
        row.featureVersion === DISCOVERY_FEATURE_VERSION &&
        row.featureAsOf instanceof Date &&
        !Number.isNaN(row.featureAsOf.getTime()) &&
        row.featureAsOf.getTime() <= now.getTime() &&
        now.getTime() - row.featureAsOf.getTime() <=
            MAX_SNAPSHOT_AGE_HOURS * 60 * 60 * 1_000 &&
        row.availability === "available" &&
        row.prominence !== null &&
        row.momentum !== null &&
        row.growth !== null &&
        row.confidence !== null &&
        [row.prominence, row.momentum, row.growth, row.confidence].every(
            Number.isFinite,
        ) &&
        row.confidence >= MIN_CONFIDENCE
    );
}

function classifiedItem(
    row: FreshAndRisingEvidenceRow,
    reason: FreshAndRisingReason,
    score: number,
): ClassifiedItem {
    return {
        showId: row.showId,
        performer: {
            id: row.canonicalComedianId,
            uuid: row.canonicalComedianUuid,
            name: row.canonicalComedianName,
        },
        reason,
        score,
        showDate: row.showDate,
    };
}

function compareItems(left: ClassifiedItem, right: ClassifiedItem): number {
    return (
        right.score - left.score ||
        left.showDate.getTime() - right.showDate.getTime() ||
        left.showId - right.showId
    );
}

function uniqueAndLimit(
    items: ClassifiedItem[],
    limit: number,
): ClassifiedItem[] {
    const seen = new Set<number>();
    return items.sort(compareItems).filter(({ showId }) => {
        if (seen.has(showId) || seen.size >= limit) return false;
        seen.add(showId);
        return true;
    });
}

export function classifyFreshAndRisingCandidates(
    rows: readonly FreshAndRisingEvidenceRow[],
    options: ClassifyOptions,
): ClassifiedRails {
    const horizonEnd = new Date(
        options.now.getTime() + options.horizonDays * DAY_MS,
    );
    const newlyAdded: ClassifiedItem[] = [];
    const startingToBuzz: ClassifiedItem[] = [];
    const catchThemEarly: ClassifiedItem[] = [];

    for (const row of rows) {
        if (!isEligible(row, options.now, horizonEnd)) continue;
        if (row.availability === "unavailable") continue;

        const evidence = reasonEvidence(row, options.now);
        const firstDiscoveredAt = row.firstDiscoveredAt;
        if (
            firstDiscoveredAt &&
            !Number.isNaN(firstDiscoveredAt.getTime()) &&
            firstDiscoveredAt.getTime() <= options.now.getTime() &&
            options.now.getTime() - firstDiscoveredAt.getTime() <=
                NEWLY_ADDED_DAYS * DAY_MS
        ) {
            const announcement = verifiedAnnouncement(row, options.now);
            newlyAdded.push(
                classifiedItem(
                    row,
                    {
                        kind: "newly_added",
                        label: announcement
                            ? `Recently announced by ${announcement.source.trim()}`
                            : "Newly found by LaughTrack",
                        evidence,
                    },
                    firstDiscoveredAt.getTime(),
                ),
            );
        }

        if (!hasUsableSnapshot(row, options.now)) continue;
        const signals = normalizeSignals(row.featureEvidence);
        if (!signals) continue;

        const positiveMomentum =
            row.momentum >= MIN_MOMENTUM && hasMomentumSupport(signals);
        const positiveGrowth =
            row.growth >= MIN_GROWTH && hasPositiveGrowthSupport(signals);
        if (positiveMomentum || positiveGrowth) {
            const strongestSignal = positiveGrowth
                ? "Momentum is growing across recent LaughTrack signals"
                : "Recent LaughTrack interest is picking up";
            startingToBuzz.push(
                classifiedItem(
                    row,
                    {
                        kind: "starting_to_buzz",
                        label: strongestSignal,
                        evidence,
                    },
                    Math.max(row.momentum, row.growth) * 0.7 +
                        row.confidence * 0.3,
                ),
            );
        }

        if (positiveGrowth && row.prominence <= MAX_EARLY_PROMINENCE) {
            catchThemEarly.push(
                classifiedItem(
                    row,
                    {
                        kind: "catch_them_early",
                        label: "Growing now, before everyone catches on",
                        evidence,
                    },
                    row.growth * 0.45 +
                        row.momentum * 0.2 +
                        row.confidence * 0.2 +
                        (1 - Math.max(0, Math.min(1, row.prominence))) * 0.15,
                ),
            );
        }
    }

    return {
        newlyAdded: uniqueAndLimit(newlyAdded, options.limit),
        startingToBuzz: uniqueAndLimit(startingToBuzz, options.limit),
        catchThemEarly: uniqueAndLimit(catchThemEarly, options.limit),
    };
}

export function buildFreshAndRisingQuery({
    now,
    horizonEnd,
}: {
    now: Date;
    horizonEnd: Date;
}): Prisma.Sql {
    return Prisma.sql`
        WITH eligible_shows AS (
            SELECT
                s.id,
                s.date,
                s.name,
                s.first_discovered_at,
                s.tickets_sold_out,
                club.visible AS club_visible
            FROM shows s
            JOIN clubs club ON club.id = s.club_id
            WHERE club.visible = true
              AND s.date > ${now}
              AND s.date <= ${horizonEnd}
              AND s.tickets_sold_out = false
              AND COALESCE(s.name, '') !~* 'sold[ -]?out'
              AND EXISTS (
                  SELECT 1
                  FROM tickets ticket
                  WHERE ticket.show_id = s.id
                    AND ticket.sold_out = false
                    AND NULLIF(btrim(ticket.purchase_url), '') IS NOT NULL
              )
        )
        SELECT
            show.id AS show_id,
            show.date AS show_date,
            show.name AS show_name,
            show.first_discovered_at,
            show.club_visible,
            performer.performer_visible,
            performer.canonical_visible,
            show.tickets_sold_out,
            true AS has_purchase_path,
            performer.canonical_comedian_id,
            performer.canonical_comedian_uuid,
            performer.canonical_comedian_name,
            snapshot.feature_version,
            snapshot.as_of AS feature_as_of,
            snapshot.prominence,
            snapshot.momentum,
            snapshot.growth,
            snapshot.confidence,
            snapshot.availability,
            snapshot.evidence AS feature_evidence
        FROM eligible_shows show
        JOIN LATERAL (
            SELECT
                performer.visible AS performer_visible,
                canonical.visible AS canonical_visible,
                canonical.id AS canonical_comedian_id,
                canonical.uuid AS canonical_comedian_uuid,
                canonical.name AS canonical_comedian_name
            FROM lineup_items lineup
            JOIN comedians performer ON performer.uuid = lineup.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(performer.parent_comedian_id, performer.id)
            WHERE lineup.show_id = show.id
              AND performer.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM tagged_comedians tagged
                  JOIN tags tag ON tag.id = tagged.tag_id
                  WHERE tagged.comedian_id IN (performer.uuid, canonical.uuid)
                    AND tag."restrictContent" = true
              )
            ORDER BY canonical.popularity DESC, canonical.id ASC
            LIMIT 1
        ) performer ON true
        LEFT JOIN LATERAL (
            SELECT
                feature_version,
                as_of,
                prominence,
                momentum,
                growth,
                confidence,
                availability,
                evidence
            FROM discovery_show_feature_snapshots snapshot
            WHERE snapshot.show_id = show.id
              AND snapshot.feature_version = ${DISCOVERY_FEATURE_VERSION}
              AND snapshot.as_of <= ${now}
            ORDER BY snapshot.as_of DESC, snapshot.computed_at DESC, snapshot.id DESC
            LIMIT 1
        ) snapshot ON true
        ORDER BY show.date ASC, show.id ASC
    `;
}

function rowToEvidence(row: FreshAndRisingQueryRow): FreshAndRisingEvidenceRow {
    return {
        showId: row.show_id,
        showDate: row.show_date,
        showName: row.show_name,
        firstDiscoveredAt: row.first_discovered_at,
        clubVisible: row.club_visible,
        performerVisible: row.performer_visible,
        canonicalVisible: row.canonical_visible,
        ticketsSoldOut: row.tickets_sold_out,
        hasPurchasePath: row.has_purchase_path,
        canonicalComedianId: row.canonical_comedian_id,
        canonicalComedianUuid: row.canonical_comedian_uuid,
        canonicalComedianName: row.canonical_comedian_name,
        featureVersion: row.feature_version,
        featureAsOf: row.feature_as_of,
        prominence: row.prominence,
        momentum: row.momentum,
        growth: row.growth,
        confidence: row.confidence,
        availability: row.availability,
        featureEvidence: row.feature_evidence,
    };
}

function emptyRails(): FreshAndRisingRails {
    return {
        newlyAdded: {
            railKey: "newly_added",
            label: "Newly added",
            items: [],
        },
        startingToBuzz: {
            railKey: "starting_to_buzz",
            label: "Starting to buzz",
            items: [],
        },
        catchThemEarly: {
            railKey: "catch_them_early",
            label: "Catch them early",
            items: [],
        },
    };
}

export async function getFreshAndRisingRails(
    options: FreshAndRisingOptions = {},
): Promise<FreshAndRisingRails> {
    const rails = emptyRails();
    const now = options.now ?? new Date();
    if (Number.isNaN(now.getTime())) return rails;

    const horizonDays = Math.max(
        1,
        Math.min(365, Math.trunc(options.horizonDays ?? DEFAULT_HORIZON_DAYS)),
    );
    const limit = Math.max(
        1,
        Math.min(MAX_LIMIT, Math.trunc(options.limit ?? DEFAULT_LIMIT)),
    );
    const horizonEnd = new Date(now.getTime() + horizonDays * DAY_MS);
    const rows = await db.$queryRaw<FreshAndRisingQueryRow[]>(
        buildFreshAndRisingQuery({ now, horizonEnd }),
    );
    if (rows.length === 0) return rails;

    const classified = classifyFreshAndRisingCandidates(
        rows.map(rowToEvidence),
        { now, horizonDays, limit },
    );
    const showIds = [
        ...new Set(
            [
                ...classified.newlyAdded,
                ...classified.startingToBuzz,
                ...classified.catchThemEarly,
            ].map(({ showId }) => showId),
        ),
    ];
    if (showIds.length === 0) return rails;

    const shows = await findShowsForHome(
        { id: { in: showIds }, club: { visible: true } },
        [{ date: "asc" }, { id: "asc" }],
        showIds.length,
    );
    const showsById = new Map(shows.map((show) => [show.id, show]));
    const hydrate = (items: ClassifiedItem[]): FreshAndRisingRailItem[] =>
        items.flatMap(({ score: _score, showDate: _showDate, ...item }) => {
            const show = showsById.get(item.showId);
            if (!show) return [];
            const { showId: _showId, ...rest } = item;
            return [{ ...rest, show }];
        });

    rails.newlyAdded.items = hydrate(classified.newlyAdded);
    rails.startingToBuzz.items = hydrate(classified.startingToBuzz);
    rails.catchThemEarly.items = hydrate(classified.catchThemEarly);
    return rails;
}
