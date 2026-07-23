import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";

const DAY_MS = 24 * 60 * 60 * 1000;

export const FAVORITE_GROWTH_RECENT_DAYS = 7;
export const FAVORITE_GROWTH_BASELINE_DAYS = 28;

export interface FavoriteGrowthWindows {
    baselineStart: Date;
    recentStart: Date;
    end: Date;
}

export interface FavoriteGrowthAggregate {
    comedianId: string;
    recentCount: number;
    baselineCount: number;
}

type FavoriteGrowthRow = {
    comedian_id: string;
    recent_count: bigint | number;
    baseline_count: bigint | number;
};

export function getFavoriteGrowthWindows(asOf: Date): FavoriteGrowthWindows {
    if (Number.isNaN(asOf.getTime())) {
        throw new RangeError("asOf must be a valid date");
    }

    const end = new Date(
        Date.UTC(asOf.getUTCFullYear(), asOf.getUTCMonth(), asOf.getUTCDate()),
    );
    const recentStart = new Date(
        end.getTime() - FAVORITE_GROWTH_RECENT_DAYS * DAY_MS,
    );
    const baselineStart = new Date(
        recentStart.getTime() - FAVORITE_GROWTH_BASELINE_DAYS * DAY_MS,
    );

    return { baselineStart, recentStart, end };
}

export function buildFavoriteGrowthQuery(asOf: Date): Prisma.Sql {
    const { baselineStart, recentStart, end } = getFavoriteGrowthWindows(asOf);

    return Prisma.sql`
        SELECT
            comedian_id,
            COUNT(*) FILTER (
                WHERE created_at >= ${recentStart}
                  AND created_at < ${end}
            ) AS recent_count,
            COUNT(*) FILTER (
                WHERE created_at >= ${baselineStart}
                  AND created_at < ${recentStart}
            ) AS baseline_count
        FROM favorite_comedians
        WHERE created_at IS NOT NULL
          AND created_at >= ${baselineStart}
          AND created_at < ${end}
        GROUP BY comedian_id
        ORDER BY comedian_id
    `;
}

export async function getFavoriteGrowth(
    asOf: Date,
): Promise<FavoriteGrowthAggregate[]> {
    const rows = await db.$queryRaw<FavoriteGrowthRow[]>(
        buildFavoriteGrowthQuery(asOf),
    );

    return rows.map((row) => ({
        comedianId: row.comedian_id,
        recentCount: Number(row.recent_count),
        baselineCount: Number(row.baseline_count),
    }));
}
