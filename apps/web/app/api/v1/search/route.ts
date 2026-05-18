import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const SEARCH_TYPES = ["show", "comedian", "club", "podcast"] as const;
type SearchEntityType = (typeof SEARCH_TYPES)[number];

type GlobalSearchResult = {
    id: string;
    entityType: SearchEntityType;
    title: string;
    subtitle: string | null;
    href: string;
    imageUrl: string | null;
};

function normalizeType(value: string | null): SearchEntityType | "all" {
    if (value && SEARCH_TYPES.includes(value as SearchEntityType)) {
        return value as SearchEntityType;
    }
    return "all";
}

function containsQuery(query: string) {
    return { contains: query, mode: "insensitive" as const };
}

const PUBLIC_PODCAST_OWNERSHIP_WHERE = {
    comedianPodcasts: {
        some: {
            reviewStatus: "accepted",
            associationType: { in: ["host", "owner"] },
        },
    },
};

function profileHref(kind: "comedian" | "club", name: string) {
    return `/${kind}/${encodeURIComponent(name)}`;
}

async function searchPodcasts(
    query: string,
    limit: number,
): Promise<{ data: GlobalSearchResult[]; total: number }> {
    const where = {
        AND: [
            PUBLIC_PODCAST_OWNERSHIP_WHERE,
            {
                OR: [
                    { title: containsQuery(query) },
                    { authorName: containsQuery(query) },
                ],
            },
        ],
    };

    const [total, podcasts] = await Promise.all([
        db.podcast.count({ where }),
        db.podcast.findMany({
            where,
            select: {
                id: true,
                slug: true,
                title: true,
                authorName: true,
                imageUrl: true,
                websiteUrl: true,
                feedUrl: true,
            },
            orderBy: [{ title: "asc" }, { id: "asc" }],
            take: limit,
        }),
    ]);

    return {
        total,
        data: podcasts.map((podcast) => ({
            id: `podcast-${podcast.id}`,
            entityType: "podcast",
            title: podcast.title,
            subtitle: podcast.authorName,
            href:
                podcast.websiteUrl ??
                podcast.feedUrl ??
                `/podcast/${podcast.slug}`,
            imageUrl: podcast.imageUrl,
        })),
    };
}

async function searchShows(
    query: string,
    limit: number,
): Promise<{ data: GlobalSearchResult[]; total: number }> {
    const where = {
        date: { gte: new Date() },
        club: { visible: true },
        name: containsQuery(query),
    };

    const [total, shows] = await Promise.all([
        db.show.count({ where }),
        db.show.findMany({
            where,
            select: {
                id: true,
                name: true,
                date: true,
                club: {
                    select: {
                        name: true,
                        city: true,
                        state: true,
                    },
                },
            },
            orderBy: [{ date: "asc" }, { id: "asc" }],
            take: limit,
        }),
    ]);

    return {
        total,
        data: shows.map((show) => ({
            id: `show-${show.id}`,
            entityType: "show",
            title: show.name ?? "Untitled show",
            subtitle: [show.club.name, show.club.city, show.club.state]
                .filter(Boolean)
                .join(" · "),
            href: `/show/${show.id}`,
            imageUrl: null,
        })),
    };
}

async function searchComedians(
    query: string,
    limit: number,
): Promise<{ data: GlobalSearchResult[]; total: number }> {
    const where = {
        parentComedian: { is: null },
        name: containsQuery(query),
    };

    const [total, comedians] = await Promise.all([
        db.comedian.count({ where }),
        db.comedian.findMany({
            where,
            select: {
                id: true,
                name: true,
            },
            orderBy: [{ popularity: "desc" }, { name: "asc" }],
            take: limit,
        }),
    ]);

    return {
        total,
        data: comedians.map((comedian) => ({
            id: `comedian-${comedian.id}`,
            entityType: "comedian",
            title: comedian.name,
            subtitle: "Comedian",
            href: profileHref("comedian", comedian.name),
            imageUrl: null,
        })),
    };
}

async function searchClubs(
    query: string,
    limit: number,
): Promise<{ data: GlobalSearchResult[]; total: number }> {
    const where = {
        visible: true,
        status: "active",
        clubType: { not: "festival" },
        OR: [{ name: containsQuery(query) }, { city: containsQuery(query) }],
    };

    const [total, clubs] = await Promise.all([
        db.club.count({ where }),
        db.club.findMany({
            where,
            select: {
                id: true,
                name: true,
                city: true,
                state: true,
            },
            orderBy: [{ totalShows: "desc" }, { name: "asc" }],
            take: limit,
        }),
    ]);

    return {
        total,
        data: clubs.map((club) => ({
            id: `club-${club.id}`,
            entityType: "club",
            title: club.name,
            subtitle: [club.city, club.state].filter(Boolean).join(", "),
            href: profileHref("club", club.name),
            imageUrl: null,
        })),
    };
}

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "global-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const query = (sp.get("q") ?? "").trim();
    const selectedType = normalizeType(sp.get("type"));
    const limit = Math.min(Math.max(Number(sp.get("limit")) || 8, 1), 25);

    if (!query) {
        return NextResponse.json(
            {
                data: [],
                total: 0,
                totals: { all: 0, show: 0, comedian: 0, club: 0, podcast: 0 },
            },
            { headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const requestedTypes =
            selectedType === "all" ? SEARCH_TYPES : [selectedType];
        const searches = {
            show: searchShows,
            comedian: searchComedians,
            club: searchClubs,
            podcast: searchPodcasts,
        };

        const entries = await Promise.all(
            requestedTypes.map(async (type) => ({
                type,
                result: await searches[type](query, limit),
            })),
        );

        const totals = { all: 0, show: 0, comedian: 0, club: 0, podcast: 0 };
        const data: GlobalSearchResult[] = [];
        for (const entry of entries) {
            totals[entry.type] = entry.result.total;
            totals.all += entry.result.total;
            data.push(...entry.result.data);
        }

        return NextResponse.json(
            { data, total: totals.all, totals },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/search error:", error);
        return NextResponse.json(
            { error: "Failed to fetch search results" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
