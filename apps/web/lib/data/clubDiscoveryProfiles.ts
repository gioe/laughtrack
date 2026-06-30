export const CLUB_DISCOVERY_PROFILE_CLASSIFIED_THRESHOLD = 0.6;

const UNKNOWN_SHOW_TYPE = "unknown";
const COMEDY_SHOW_TYPES = new Set([
    "standup",
    "improv",
    "sketch",
    "musical_comedy",
    "open_mic",
    "variety",
    "podcast",
]);

export interface ClubDiscoveryProfileShowRow {
    showType: string | null;
}

export interface BuildClubDiscoveryProfileInput {
    clubId: number;
    rows: ClubDiscoveryProfileShowRow[];
    computedAt?: Date;
}

export interface ClubDiscoveryProfileSummary {
    clubId: number;
    primaryShowType: string | null;
    showTypeCounts: Record<string, number>;
    comedyShowCount: number;
    nonComedyShowCount: number;
    mixedProgramming: boolean;
    confidence: number;
    computedAt: Date;
}

interface RankedShowType {
    showType: string;
    count: number;
}

export function buildClubDiscoveryProfile({
    clubId,
    rows,
    computedAt = new Date(),
}: BuildClubDiscoveryProfileInput): ClubDiscoveryProfileSummary {
    const showTypeCounts = countShowTypes(rows);
    const totalRows = rows.length;
    const classified = rankClassifiedShowTypes(showTypeCounts);

    if (totalRows === 0) {
        return {
            clubId,
            primaryShowType: UNKNOWN_SHOW_TYPE,
            showTypeCounts,
            comedyShowCount: 0,
            nonComedyShowCount: 0,
            mixedProgramming: false,
            confidence: 0,
            computedAt,
        };
    }

    if (classified.length === 0) {
        return {
            clubId,
            primaryShowType: UNKNOWN_SHOW_TYPE,
            showTypeCounts,
            comedyShowCount: 0,
            nonComedyShowCount: 0,
            mixedProgramming: false,
            confidence: 0,
            computedAt,
        };
    }

    const dominant = classified[0];
    const classifiedCount = classified.reduce(
        (sum, entry) => sum + entry.count,
        0,
    );
    const classifiedShare = dominant.count / classifiedCount;
    const primaryShowType =
        classifiedShare >= CLUB_DISCOVERY_PROFILE_CLASSIFIED_THRESHOLD
            ? dominant.showType
            : null;

    return {
        clubId,
        primaryShowType,
        showTypeCounts,
        comedyShowCount: countComedyShows(showTypeCounts),
        nonComedyShowCount: countNonComedyShows(showTypeCounts),
        mixedProgramming: primaryShowType === null,
        confidence: roundRatio(dominant.count / totalRows),
        computedAt,
    };
}

function countShowTypes(
    rows: ClubDiscoveryProfileShowRow[],
): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const row of rows) {
        const showType = normalizeShowType(row.showType);
        counts[showType] = (counts[showType] ?? 0) + 1;
    }
    return counts;
}

function normalizeShowType(showType: string | null): string {
    const normalized = showType?.trim();
    return normalized ? normalized : UNKNOWN_SHOW_TYPE;
}

function rankClassifiedShowTypes(
    counts: Record<string, number>,
): RankedShowType[] {
    return Object.entries(counts)
        .filter(([showType]) => showType !== UNKNOWN_SHOW_TYPE)
        .map(([showType, count]) => ({ showType, count }))
        .sort(
            (left, right) =>
                right.count - left.count ||
                left.showType.localeCompare(right.showType),
        );
}

function countComedyShows(counts: Record<string, number>): number {
    return Object.entries(counts).reduce(
        (sum, [showType, count]) =>
            COMEDY_SHOW_TYPES.has(showType) ? sum + count : sum,
        0,
    );
}

function countNonComedyShows(counts: Record<string, number>): number {
    return Object.entries(counts).reduce((sum, [showType, count]) => {
        if (showType === UNKNOWN_SHOW_TYPE || COMEDY_SHOW_TYPES.has(showType)) {
            return sum;
        }
        return sum + count;
    }, 0);
}

function roundRatio(value: number): number {
    return Math.round(value * 100) / 100;
}
