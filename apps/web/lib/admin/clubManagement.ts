import { db } from "@/lib/db";
import {
    buildClubHeroImageUrl,
    buildClubImageAssetUrl,
    buildClubImageUrl,
} from "@/util/imageUtil";

export type AdminClubListItem = {
    id: number;
    name: string;
    city: string | null;
    state: string | null;
    website: string;
    popularity: number;
    hasImage: boolean;
    iconUrl: string;
    heroUrl: string;
    activeImageAsset: {
        id: number;
        sourceImageUrl: string;
        originalPath: string;
        iconPath: string | null;
        heroPath: string | null;
        iconUrl: string | null;
        heroUrl: string | null;
        mimeType: string | null;
        width: number | null;
        height: number | null;
    } | null;
    visible: boolean;
    status: string;
    clubType: string;
    closedAt: string | null;
    totalShows: number;
    scrapedShowCount: number;
    latestScrapeAt: string | null;
    latestScrapeBy: string | null;
    scrapingSources: Array<{
        id: number;
        platform: string;
        scraperKey: string;
        enabled: boolean;
        priority: number;
    }>;
    chain: {
        id: number;
        name: string;
        slug: string;
        website: string | null;
    } | null;
};

export type AdminClubGroup = {
    key: string;
    chain: AdminClubListItem["chain"];
    clubs: AdminClubListItem[];
    totals: {
        clubCount: number;
        visibleCount: number;
        activeCount: number;
        scrapedShowCount: number;
    };
};

function toIso(value: Date | null | undefined) {
    return value ? value.toISOString() : null;
}

function groupClubs(clubs: AdminClubListItem[]): AdminClubGroup[] {
    const grouped = new Map<string, AdminClubListItem[]>();

    for (const club of clubs) {
        const key = club.chain ? `chain-${club.chain.id}` : "unchained";
        const rows = grouped.get(key) ?? [];
        rows.push(club);
        grouped.set(key, rows);
    }

    return Array.from(grouped.entries())
        .map(([key, rows]) => {
            const chain = rows[0].chain;
            return {
                key,
                chain,
                clubs: rows.sort((a, b) =>
                    a.name.localeCompare(b.name, undefined, {
                        sensitivity: "base",
                    }),
                ),
                totals: {
                    clubCount: rows.length,
                    visibleCount: rows.filter((club) => club.visible).length,
                    activeCount: rows.filter((club) => club.status === "active")
                        .length,
                    scrapedShowCount: rows.reduce(
                        (sum, club) => sum + club.scrapedShowCount,
                        0,
                    ),
                },
            };
        })
        .sort((a, b) => {
            if (!a.chain && b.chain) return 1;
            if (a.chain && !b.chain) return -1;
            const clubCountDelta = b.totals.clubCount - a.totals.clubCount;
            if (clubCountDelta !== 0) return clubCountDelta;
            return (a.chain?.name ?? "Unchained").localeCompare(
                b.chain?.name ?? "Unchained",
                undefined,
                { sensitivity: "base" },
            );
        });
}

export async function listAdminClubGroups(): Promise<AdminClubGroup[]> {
    const clubs = await db.club.findMany({
        select: {
            id: true,
            name: true,
            city: true,
            state: true,
            website: true,
            popularity: true,
            hasImage: true,
            visible: true,
            status: true,
            clubType: true,
            closedAt: true,
            totalShows: true,
            chain: {
                select: {
                    id: true,
                    name: true,
                    slug: true,
                    website: true,
                },
            },
            scrapingSources: {
                select: {
                    id: true,
                    platform: true,
                    scraperKey: true,
                    enabled: true,
                    priority: true,
                },
                orderBy: [{ priority: "asc" }, { id: "asc" }],
            },
            shows: {
                select: {
                    lastScrapedDate: true,
                    lastScrapedBy: true,
                },
                orderBy: [{ lastScrapedDate: "desc" }, { id: "desc" }],
                take: 1,
            },
            imageAssets: {
                where: { isActive: true },
                select: {
                    id: true,
                    sourceImageUrl: true,
                    originalPath: true,
                    iconPath: true,
                    heroPath: true,
                    mimeType: true,
                    width: true,
                    height: true,
                },
                orderBy: { publishedAt: "desc" },
                take: 1,
            },
            _count: {
                select: {
                    shows: true,
                },
            },
        },
        orderBy: [{ chain: { name: "asc" } }, { name: "asc" }],
    });

    return groupClubs(
        clubs.map((club) => {
            const latestShow = club.shows[0] ?? null;
            const activeImageAsset = club.imageAssets?.[0] ?? null;
            const activeIconUrl = activeImageAsset?.iconPath
                ? buildClubImageAssetUrl(activeImageAsset.iconPath)
                : null;
            return {
                id: club.id,
                name: club.name,
                city: club.city,
                state: club.state,
                website: club.website,
                popularity: club.popularity,
                hasImage: club.hasImage,
                iconUrl:
                    activeIconUrl ??
                    buildClubImageUrl(club.name, club.hasImage),
                heroUrl: buildClubHeroImageUrl(activeImageAsset?.heroPath),
                activeImageAsset: activeImageAsset
                    ? {
                          id: activeImageAsset.id,
                          sourceImageUrl: activeImageAsset.sourceImageUrl,
                          originalPath: activeImageAsset.originalPath,
                          iconPath: activeImageAsset.iconPath,
                          heroPath: activeImageAsset.heroPath,
                          iconUrl: activeIconUrl,
                          heroUrl: activeImageAsset.heroPath
                              ? buildClubImageAssetUrl(
                                    activeImageAsset.heroPath,
                                )
                              : null,
                          mimeType: activeImageAsset.mimeType,
                          width: activeImageAsset.width,
                          height: activeImageAsset.height,
                      }
                    : null,
                visible: club.visible ?? true,
                status: club.status,
                clubType: club.clubType,
                closedAt: toIso(club.closedAt),
                totalShows: club.totalShows,
                scrapedShowCount: club._count.shows,
                latestScrapeAt: toIso(latestShow?.lastScrapedDate),
                latestScrapeBy: latestShow?.lastScrapedBy ?? null,
                scrapingSources: club.scrapingSources.map((source) => ({
                    id: source.id,
                    platform: source.platform,
                    scraperKey: source.scraperKey,
                    enabled: source.enabled,
                    priority: source.priority,
                })),
                chain: club.chain,
            };
        }),
    );
}
