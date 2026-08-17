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

export type FreshAndRisingReasonKind = "starting_to_buzz";

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
    startingToBuzz: FreshAndRisingRail;
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
}

interface ClassifiedItem {
    showId: number;
    performer: FreshAndRisingRailItem["performer"];
    reason: FreshAndRisingReason;
    score: number;
    showDate: Date;
}

interface ClassifiedRails {
    startingToBuzz: ClassifiedItem[];
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

function reasonEvidence(
    row: FreshAndRisingEvidenceRow,
): FreshAndRisingReasonEvidence {
    return {
        firstDiscoveredAt: row.firstDiscoveredAt,
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

function freshnessBoost(firstDiscoveredAt: Date | null, now: Date): number {
    if (
        !firstDiscoveredAt ||
        Number.isNaN(firstDiscoveredAt.getTime()) ||
        firstDiscoveredAt.getTime() > now.getTime()
    ) {
        return 0;
    }
    const ageDays = (now.getTime() - firstDiscoveredAt.getTime()) / DAY_MS;
    return Math.max(0, 1 - ageDays / NEWLY_ADDED_DAYS);
}

function momentumRankingScore(
    row: FreshAndRisingEvidenceRow & {
        prominence: number;
        momentum: number;
        growth: number;
        confidence: number;
    },
    now: Date,
): number {
    const lowerProminenceBoost = 1 - Math.max(0, Math.min(1, row.prominence));
    return (
        Math.max(row.momentum, row.growth) * 0.55 +
        row.confidence * 0.25 +
        lowerProminenceBoost * 0.1 +
        freshnessBoost(row.firstDiscoveredAt, now) * 0.1
    );
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
    const startingToBuzz: ClassifiedItem[] = [];

    for (const row of rows) {
        if (!isEligible(row, options.now, horizonEnd)) continue;
        if (row.availability === "unavailable") continue;

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
                        evidence: reasonEvidence(row),
                    },
                    momentumRankingScore(row, options.now),
                ),
            );
        }
    }

    return {
        startingToBuzz: uniqueAndLimit(startingToBuzz, options.limit),
    };
}

export function buildFreshAndRisingQuery({
    now,
    horizonEnd,
}: {
    now: Date;
    horizonEnd: Date;
}): Prisma.Sql {
    const snapshotFreshAfter = new Date(
        now.getTime() - MAX_SNAPSHOT_AGE_HOURS * 60 * 60 * 1_000,
    );

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
                  FROM discovery_show_feature_snapshots candidate_snapshot
                  WHERE candidate_snapshot.show_id = s.id
                    AND candidate_snapshot.feature_version = ${DISCOVERY_FEATURE_VERSION}
                    AND candidate_snapshot.as_of >= ${snapshotFreshAfter}
                    AND candidate_snapshot.as_of <= ${now}
                    AND candidate_snapshot.availability = 'available'
                    AND candidate_snapshot.confidence >= ${MIN_CONFIDENCE}
                    AND (
                        candidate_snapshot.momentum >= ${MIN_MOMENTUM}
                        OR candidate_snapshot.growth >= ${MIN_GROWTH}
                    )
              )
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
        startingToBuzz: {
            railKey: "starting_to_buzz",
            label: "Shows gaining momentum",
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
        ...new Set(classified.startingToBuzz.map(({ showId }) => showId)),
    ];
    if (showIds.length === 0) return rails;

    const shows = await findShowsForHome(
        { id: { in: showIds }, club: { visible: true } },
        [{ date: "asc" }, { id: "asc" }],
        showIds.length,
        { requireLineup: true },
    );
    const showsById = new Map(shows.map((show) => [show.id, show]));
    const hydrate = (items: ClassifiedItem[]): FreshAndRisingRailItem[] =>
        items.flatMap(({ score: _score, showDate: _showDate, ...item }) => {
            const show = showsById.get(item.showId);
            if (!show) return [];
            const { showId: _showId, ...rest } = item;
            return [{ ...rest, show }];
        });

    rails.startingToBuzz.items = hydrate(classified.startingToBuzz);
    return rails;
}
