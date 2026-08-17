import zipcodes from "zipcodes";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { findShowsForHome } from "./findShowsForHome";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    selectDiverseShowItemsByTime,
} from "./showRailSelection";

const DAY_MS = 24 * 60 * 60 * 1_000;
const DEFAULT_HORIZON_DAYS = 90;
const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 50;
const MAX_SHORT_RUN_APPEARANCES = 3;
const MAX_SHORT_RUN_DAYS = 7;
const HOME_LOCATION_MAX_AGE_DAYS = 730;
const MIN_HISTORY_COVERAGE_DAYS = 365;
const MIN_HISTORY_SHOWS = 10;
const BACK_AFTER_DAYS = 270;
const MAX_RARE_PRIOR_APPEARANCES = 2;
const TOURING_SCARCITY_RAIL_LIMIT = 8;
export const TOURING_SCARCITY_POPULARITY_FLOOR = 0.4;

export type TouringScarcityReasonKind =
    | "just_passing_through"
    | "rare_return"
    | "back_after_a_while";

export interface TouringScarcityMarket {
    city: string;
    state: string;
    country?: string | null;
}

export interface TouringScarcityReasonEvidence {
    canonicalComedianId: number;
    localAppearanceCount: number;
    horizonDays: number;
    runStart: Date;
    runEnd: Date;
    homeMarket: TouringScarcityMarket | null;
    requestedMarket: TouringScarcityMarket | null;
    priorLocalAppearanceCount: number;
    lastLocalAppearanceAt: Date | null;
    historyCoverageStart: Date | null;
    historyCoverageShowCount: number;
}

export interface TouringScarcityReason {
    kind: TouringScarcityReasonKind;
    label: string;
    evidence: TouringScarcityReasonEvidence;
}

export interface TouringScarcityRailItem {
    show: ShowDTO;
    performer: {
        id: number;
        uuid: string;
        name: string;
    };
    reason: TouringScarcityReason;
}

export interface TouringScarcityRail {
    railKey: "just_passing_through";
    label: string;
    items: TouringScarcityRailItem[];
}

export interface TouringScarcityRails {
    justPassingThrough: TouringScarcityRail;
}

export interface TouringScarcityOptions {
    zipCode: string;
    radiusMiles?: number;
    now?: Date;
    horizonDays?: number;
    limit?: number;
}

/**
 * One row per canonical-performer/show pair. The SQL loader filters these
 * fields, while keeping them in the row makes the classifier defensive and
 * independently testable.
 */
export interface TouringScarcityEvidenceRow {
    showId: number;
    showDate: Date;
    showName: string | null;
    clubVisible: boolean;
    performerVisible: boolean;
    canonicalVisible: boolean;
    withinRadius: boolean;
    ticketsSoldOut: boolean;
    hasPurchasePath: boolean;
    canonicalComedianId: number;
    canonicalComedianUuid: string;
    canonicalComedianName: string;
    canonicalPopularity: number;
    homeCity: string | null;
    homeState: string | null;
    homeCountry: string | null;
    homeZipCode: string | null;
    homeLocationUpdatedAt: Date | null;
    localAppearanceCount: number | bigint;
    runStart: Date;
    runEnd: Date;
    priorLocalAppearanceCount: number | bigint;
    lastLocalAppearanceAt: Date | null;
    historyCoverageStart: Date | null;
    historyCoverageShowCount: number | bigint;
}

interface ClassifiedItem {
    showId: number;
    performer: TouringScarcityRailItem["performer"];
    reason: TouringScarcityReason;
}

interface ClassifiedRails {
    justPassingThrough: ClassifiedItem[];
}

interface ClassifyOptions {
    now: Date;
    horizonDays: number;
    nearbyZips: readonly string[];
    requestedMarket: TouringScarcityMarket | null;
    limit: number;
}

type TouringScarcityQueryRow = {
    show_id: number;
    show_date: Date;
    show_name: string | null;
    club_visible: boolean;
    performer_visible: boolean;
    canonical_visible: boolean;
    within_radius: boolean;
    tickets_sold_out: boolean;
    has_purchase_path: boolean;
    canonical_comedian_id: number;
    canonical_comedian_uuid: string;
    canonical_comedian_name: string;
    canonical_popularity: number;
    home_city: string | null;
    home_state: string | null;
    home_country: string | null;
    home_zip_code: string | null;
    home_location_updated_at: Date | null;
    local_appearance_count: number | bigint;
    run_start: Date;
    run_end: Date;
    prior_local_appearance_count: number | bigint;
    last_local_appearance_at: Date | null;
    history_coverage_start: Date | null;
    history_coverage_show_count: number | bigint;
};

function normalized(value: string | null | undefined): string {
    return value?.trim().toLocaleLowerCase("en-US") ?? "";
}

function safeCount(value: number | bigint): number {
    return Number(value);
}

function monthsBetween(earlier: Date, later: Date): number {
    return Math.max(
        1,
        Math.round((later.getTime() - earlier.getTime()) / (30 * DAY_MS)),
    );
}

function yearsOfCoverage(start: Date, now: Date): number {
    return Math.max(
        1,
        Math.floor((now.getTime() - start.getTime()) / (365 * DAY_MS)),
    );
}

function titleSaysSoldOut(name: string | null): boolean {
    return /sold[ -]?out/i.test(name ?? "");
}

function isEligibleRow(
    row: TouringScarcityEvidenceRow,
    now: Date,
    horizonEnd: Date,
): boolean {
    return (
        row.clubVisible &&
        row.performerVisible &&
        row.canonicalVisible &&
        row.withinRadius &&
        !row.ticketsSoldOut &&
        !titleSaysSoldOut(row.showName) &&
        row.hasPurchasePath &&
        row.showDate.getTime() > now.getTime() &&
        row.showDate.getTime() <= horizonEnd.getTime()
    );
}

function knownOutsideHomeMarket(
    row: TouringScarcityEvidenceRow,
    options: ClassifyOptions,
): TouringScarcityMarket | null {
    const { requestedMarket, nearbyZips, now } = options;
    if (
        !requestedMarket ||
        !row.homeCity?.trim() ||
        !row.homeState?.trim() ||
        !row.homeLocationUpdatedAt ||
        now.getTime() - row.homeLocationUpdatedAt.getTime() >
            HOME_LOCATION_MAX_AGE_DAYS * DAY_MS
    ) {
        return null;
    }

    const homeZip = row.homeZipCode?.trim();
    const isOutside = homeZip
        ? !nearbyZips.includes(homeZip)
        : normalized(row.homeState) !== normalized(requestedMarket.state);
    if (!isOutside) return null;

    return {
        city: row.homeCity.trim(),
        state: row.homeState.trim(),
        country: row.homeCountry,
    };
}

function evidence(
    row: TouringScarcityEvidenceRow,
    options: ClassifyOptions,
    homeMarket: TouringScarcityMarket | null,
): TouringScarcityReasonEvidence {
    return {
        canonicalComedianId: row.canonicalComedianId,
        localAppearanceCount: safeCount(row.localAppearanceCount),
        horizonDays: options.horizonDays,
        runStart: row.runStart,
        runEnd: row.runEnd,
        homeMarket,
        requestedMarket: options.requestedMarket,
        priorLocalAppearanceCount: safeCount(row.priorLocalAppearanceCount),
        lastLocalAppearanceAt: row.lastLocalAppearanceAt,
        historyCoverageStart: row.historyCoverageStart,
        historyCoverageShowCount: safeCount(row.historyCoverageShowCount),
    };
}

function baseItem(
    row: TouringScarcityEvidenceRow,
    reason: TouringScarcityReason,
): ClassifiedItem {
    return {
        showId: row.showId,
        performer: {
            id: row.canonicalComedianId,
            uuid: row.canonicalComedianUuid,
            name: row.canonicalComedianName,
        },
        reason,
    };
}

function appendUnique(
    items: ClassifiedItem[],
    item: ClassifiedItem,
    limit: number,
): void {
    if (
        items.length >= limit ||
        items.some((existing) => existing.showId === item.showId)
    ) {
        return;
    }
    items.push(item);
}

/** Pure, deterministic evidence classifier used by the DB-backed provider. */
export function classifyTouringScarcityCandidates(
    rows: readonly TouringScarcityEvidenceRow[],
    options: ClassifyOptions,
): ClassifiedRails {
    const horizonEnd = new Date(
        options.now.getTime() + options.horizonDays * DAY_MS,
    );
    const result: ClassifiedRails = {
        justPassingThrough: [],
    };

    const eligibleRows = rows
        .filter((row) => isEligibleRow(row, options.now, horizonEnd))
        .sort(
            (left, right) =>
                left.showDate.getTime() - right.showDate.getTime() ||
                left.showId - right.showId ||
                left.canonicalComedianId - right.canonicalComedianId,
        );

    for (const row of eligibleRows) {
        const localCount = safeCount(row.localAppearanceCount);
        const runDays =
            (row.runEnd.getTime() - row.runStart.getTime()) / DAY_MS;
        const homeMarket = knownOutsideHomeMarket(row, options);
        const meetsPopularityFloor =
            row.canonicalPopularity > TOURING_SCARCITY_POPULARITY_FLOOR;
        if (
            meetsPopularityFloor &&
            homeMarket &&
            localCount <= MAX_SHORT_RUN_APPEARANCES &&
            runDays <= MAX_SHORT_RUN_DAYS
        ) {
            appendUnique(
                result.justPassingThrough,
                baseItem(row, {
                    kind: "just_passing_through",
                    label: `Visiting from ${homeMarket.city}, ${homeMarket.state} for ${localCount} local ${localCount === 1 ? "date" : "dates"}`,
                    evidence: evidence(row, options, homeMarket),
                }),
                Math.min(options.limit, TOURING_SCARCITY_RAIL_LIMIT),
            );
        }

        const historyCount = safeCount(row.historyCoverageShowCount);
        const priorCount = safeCount(row.priorLocalAppearanceCount);
        const hasTrustworthyHistory =
            row.historyCoverageStart !== null &&
            options.now.getTime() - row.historyCoverageStart.getTime() >=
                MIN_HISTORY_COVERAGE_DAYS * DAY_MS &&
            historyCount >= MIN_HISTORY_SHOWS &&
            row.lastLocalAppearanceAt !== null &&
            priorCount > 0;
        if (
            meetsPopularityFloor &&
            hasTrustworthyHistory &&
            row.lastLocalAppearanceAt &&
            row.historyCoverageStart
        ) {
            const daysSinceLast =
                (options.now.getTime() - row.lastLocalAppearanceAt.getTime()) /
                DAY_MS;
            const rareKind: TouringScarcityReasonKind | null =
                daysSinceLast >= BACK_AFTER_DAYS
                    ? "back_after_a_while"
                    : priorCount <= MAX_RARE_PRIOR_APPEARANCES
                      ? "rare_return"
                      : null;
            if (rareKind) {
                const label =
                    rareKind === "back_after_a_while"
                        ? `Back nearby after ${monthsBetween(row.lastLocalAppearanceAt, options.now)} months`
                        : `${priorCount} prior local ${priorCount === 1 ? "date" : "dates"} in ${yearsOfCoverage(row.historyCoverageStart, options.now)}+ years of LaughTrack history`;
                appendUnique(
                    result.justPassingThrough,
                    baseItem(row, {
                        kind: rareKind,
                        label,
                        evidence: evidence(row, options, null),
                    }),
                    Math.min(options.limit, TOURING_SCARCITY_RAIL_LIMIT),
                );
            }
        }
    }

    return result;
}

export function buildTouringScarcityQuery({
    nearbyZips,
    now,
    horizonEnd,
}: {
    nearbyZips: readonly string[];
    now: Date;
    horizonEnd: Date;
}): Prisma.Sql {
    return Prisma.sql`
        WITH eligible_local_shows AS (
            SELECT
                s.id,
                s.date,
                s.name,
                s.tickets_sold_out,
                club.visible AS club_visible
            FROM shows s
            JOIN clubs club ON club.id = s.club_id
            WHERE club.visible = true
              AND club.zip_code IN (${Prisma.join(nearbyZips)})
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
        ),
        canonical_upcoming AS (
            SELECT DISTINCT
                local_show.id AS show_id,
                local_show.date AS show_date,
                local_show.name AS show_name,
                local_show.club_visible,
                performer.visible AS performer_visible,
                canonical.visible AS canonical_visible,
                local_show.tickets_sold_out,
                canonical.id AS canonical_comedian_id,
                canonical.uuid AS canonical_comedian_uuid,
                canonical.name AS canonical_comedian_name,
                canonical.popularity AS canonical_popularity,
                canonical.home_city,
                canonical.home_state,
                canonical.home_country,
                home_club.zip_code AS home_zip_code,
                canonical.home_location_updated_at
            FROM eligible_local_shows local_show
            JOIN lineup_items lineup ON lineup.show_id = local_show.id
            JOIN comedians performer ON performer.uuid = lineup.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(performer.parent_comedian_id, performer.id)
            LEFT JOIN clubs home_club ON home_club.id = canonical.home_club_id
            WHERE performer.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM tagged_comedians tagged
                  JOIN tags tag ON tag.id = tagged.tag_id
                  WHERE tagged.comedian_id IN (performer.uuid, canonical.uuid)
                    AND tag."restrictContent" = true
              )
        ),
        upcoming_totals AS (
            SELECT
                canonical_comedian_id,
                COUNT(DISTINCT show_id)::integer AS local_appearance_count,
                MIN(show_date) AS run_start,
                MAX(show_date) AS run_end
            FROM canonical_upcoming
            GROUP BY canonical_comedian_id
        ),
        local_history_coverage AS (
            SELECT
                MIN(s.date) AS history_coverage_start,
                COUNT(DISTINCT s.id)::integer AS history_coverage_show_count
            FROM shows s
            JOIN clubs club ON club.id = s.club_id
            WHERE club.visible = true
              AND club.zip_code IN (${Prisma.join(nearbyZips)})
              AND s.date < ${now}
        ),
        canonical_history AS (
            SELECT DISTINCT
                s.id AS show_id,
                s.date AS show_date,
                canonical.id AS canonical_comedian_id
            FROM shows s
            JOIN clubs club ON club.id = s.club_id
            JOIN lineup_items lineup ON lineup.show_id = s.id
            JOIN comedians performer ON performer.uuid = lineup.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(performer.parent_comedian_id, performer.id)
            WHERE club.visible = true
              AND club.zip_code IN (${Prisma.join(nearbyZips)})
              AND s.date < ${now}
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
        ),
        history_totals AS (
            SELECT
                canonical_comedian_id,
                COUNT(DISTINCT show_id)::integer AS prior_local_appearance_count,
                MAX(show_date) AS last_local_appearance_at
            FROM canonical_history
            GROUP BY canonical_comedian_id
        )
        SELECT
            upcoming.show_id,
            upcoming.show_date,
            upcoming.show_name,
            upcoming.club_visible,
            upcoming.performer_visible,
            upcoming.canonical_visible,
            true AS within_radius,
            upcoming.tickets_sold_out,
            true AS has_purchase_path,
            upcoming.canonical_comedian_id,
            upcoming.canonical_comedian_uuid,
            upcoming.canonical_comedian_name,
            upcoming.canonical_popularity,
            upcoming.home_city,
            upcoming.home_state,
            upcoming.home_country,
            upcoming.home_zip_code,
            upcoming.home_location_updated_at,
            totals.local_appearance_count,
            totals.run_start,
            totals.run_end,
            COALESCE(history.prior_local_appearance_count, 0)::integer
                AS prior_local_appearance_count,
            history.last_local_appearance_at,
            coverage.history_coverage_start,
            coverage.history_coverage_show_count
        FROM canonical_upcoming upcoming
        JOIN upcoming_totals totals
          ON totals.canonical_comedian_id = upcoming.canonical_comedian_id
        LEFT JOIN history_totals history
          ON history.canonical_comedian_id = upcoming.canonical_comedian_id
        CROSS JOIN local_history_coverage coverage
        ORDER BY upcoming.show_date ASC, upcoming.show_id ASC,
                 upcoming.canonical_comedian_id ASC
    `;
}

function rowToEvidence(
    row: TouringScarcityQueryRow,
): TouringScarcityEvidenceRow {
    return {
        showId: row.show_id,
        showDate: row.show_date,
        showName: row.show_name,
        clubVisible: row.club_visible,
        performerVisible: row.performer_visible,
        canonicalVisible: row.canonical_visible,
        withinRadius: row.within_radius,
        ticketsSoldOut: row.tickets_sold_out,
        hasPurchasePath: row.has_purchase_path,
        canonicalComedianId: row.canonical_comedian_id,
        canonicalComedianUuid: row.canonical_comedian_uuid,
        canonicalComedianName: row.canonical_comedian_name,
        canonicalPopularity: row.canonical_popularity,
        homeCity: row.home_city,
        homeState: row.home_state,
        homeCountry: row.home_country,
        homeZipCode: row.home_zip_code,
        homeLocationUpdatedAt: row.home_location_updated_at,
        localAppearanceCount: row.local_appearance_count,
        runStart: row.run_start,
        runEnd: row.run_end,
        priorLocalAppearanceCount: row.prior_local_appearance_count,
        lastLocalAppearanceAt: row.last_local_appearance_at,
        historyCoverageStart: row.history_coverage_start,
        historyCoverageShowCount: row.history_coverage_show_count,
    };
}

function requestedMarket(zipCode: string): TouringScarcityMarket | null {
    const location = zipcodes.lookup(zipCode);
    if (!location?.city || !location.state) return null;
    return {
        city: location.city,
        state: location.state,
        country: location.country,
    };
}

function emptyRails(): TouringScarcityRails {
    return {
        justPassingThrough: {
            railKey: "just_passing_through",
            label: "Here for a Limited Time",
            items: [],
        },
    };
}

export async function getTouringScarcityRails(
    options: TouringScarcityOptions,
): Promise<TouringScarcityRails> {
    const rails = emptyRails();
    if (!/^\d{5}$/.test(options.zipCode)) return rails;

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
    const nearbyZips = resolveNearbyZips(options.zipCode, options.radiusMiles);
    const horizonEnd = new Date(now.getTime() + horizonDays * DAY_MS);
    const rows = await db.$queryRaw<TouringScarcityQueryRow[]>(
        buildTouringScarcityQuery({ nearbyZips, now, horizonEnd }),
    );
    if (rows.length === 0) return rails;

    const classified = classifyTouringScarcityCandidates(
        rows.map(rowToEvidence),
        {
            now,
            horizonDays,
            nearbyZips,
            requestedMarket: requestedMarket(options.zipCode),
            limit: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
        },
    );
    const showIds = [
        ...new Set(classified.justPassingThrough.map(({ showId }) => showId)),
    ];
    if (showIds.length === 0) return rails;

    const shows = await findShowsForHome(
        { id: { in: showIds }, club: { visible: true } },
        [{ date: "asc" }, { id: "asc" }],
        showIds.length,
        { zipCode: options.zipCode },
    );
    const showsById = new Map(shows.map((show) => [show.id, show]));
    const hydrate = (items: ClassifiedItem[]): TouringScarcityRailItem[] =>
        items.flatMap((item) => {
            const show = showsById.get(item.showId);
            return show ? [{ ...item, show }] : [];
        });

    rails.justPassingThrough.items = selectDiverseShowItemsByTime(
        hydrate(classified.justPassingThrough),
        ({ show }) => show,
        limit,
    );
    return rails;
}
