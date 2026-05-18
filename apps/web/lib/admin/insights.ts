import { Prisma } from "@prisma/client";
import { z } from "zod";

type InsightParameter = {
    name: string;
    type: "string" | "integer";
    description: string;
    required?: boolean;
    defaultValue?: string | number;
    min?: number;
    max?: number;
};

export type InsightDefinition<TParams = unknown> = {
    name: string;
    primitive:
        | "clubs"
        | "shows"
        | "comedians"
        | "tickets"
        | "scrapingSources"
        | "tags"
        | "users"
        | "podcasts"
        | "emailSubscriptions";
    description: string;
    parameters: InsightParameter[];
    parseParams: (params: unknown) => TParams;
    buildQuery: (params: TParams) => Prisma.Sql;
};

const limitSchema = z.coerce.number().int().min(1).max(100).default(50);
const querySchema = z.string().trim().min(1).max(200).optional();

const searchParamsSchema = z
    .object({
        q: querySchema,
        limit: limitSchema,
    })
    .strict();

const upcomingShowsParamsSchema = searchParamsSchema.extend({
    days: z.coerce.number().int().min(1).max(365).default(30),
});

type SearchParams = z.infer<typeof searchParamsSchema>;
type UpcomingShowsParams = z.infer<typeof upcomingShowsParamsSchema>;

const searchParameters: InsightParameter[] = [
    {
        name: "q",
        type: "string",
        description: "Optional case-insensitive search text.",
    },
    {
        name: "limit",
        type: "integer",
        description: "Maximum rows to return.",
        defaultValue: 50,
        min: 1,
        max: 100,
    },
];

function likeParam(q: string) {
    return `%${q}%`;
}

function parseSearchParams(params: unknown): SearchParams {
    return searchParamsSchema.parse(params ?? {});
}

function parseUpcomingShowsParams(params: unknown): UpcomingShowsParams {
    return upcomingShowsParamsSchema.parse(params ?? {});
}

export const adminInsightRegistry = {
    "clubs.search": {
        name: "clubs.search",
        primitive: "clubs",
        description: "Find clubs by name, city, or state.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT id, name, city, state, visible, total_shows AS "totalShows"
                    FROM clubs
                    WHERE name ILIKE ${like}
                       OR city ILIKE ${like}
                       OR state ILIKE ${like}
                    ORDER BY total_shows DESC, name ASC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT id, name, city, state, visible, total_shows AS "totalShows"
                FROM clubs
                ORDER BY total_shows DESC, name ASC
                LIMIT ${limit}
            `;
        },
    },
    "shows.upcoming": {
        name: "shows.upcoming",
        primitive: "shows",
        description:
            "List upcoming shows, optionally filtered by show or club text.",
        parameters: [
            ...searchParameters,
            {
                name: "days",
                type: "integer",
                description: "Future window in days.",
                defaultValue: 30,
                min: 1,
                max: 365,
            },
        ],
        parseParams: parseUpcomingShowsParams,
        buildQuery: ({ q, limit, days }: UpcomingShowsParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT s.id, s.name, s.date, c.name AS "clubName"
                    FROM shows s
                    JOIN clubs c ON c.id = s.club_id
                    WHERE s.date >= now()
                      AND s.date < now() + (${days}::int * interval '1 day')
                      AND (s.name ILIKE ${like} OR c.name ILIKE ${like})
                    ORDER BY s.date ASC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT s.id, s.name, s.date, c.name AS "clubName"
                FROM shows s
                JOIN clubs c ON c.id = s.club_id
                WHERE s.date >= now()
                  AND s.date < now() + (${days}::int * interval '1 day')
                ORDER BY s.date ASC
                LIMIT ${limit}
            `;
        },
    },
    "comedians.search": {
        name: "comedians.search",
        primitive: "comedians",
        description: "Find comedians by name or social account.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT id, uuid, name, popularity, total_shows AS "totalShows"
                    FROM comedians
                    WHERE name ILIKE ${like}
                       OR instagram_account ILIKE ${like}
                       OR tiktok_account ILIKE ${like}
                    ORDER BY popularity DESC, name ASC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT id, uuid, name, popularity, total_shows AS "totalShows"
                FROM comedians
                ORDER BY popularity DESC, name ASC
                LIMIT ${limit}
            `;
        },
    },
    "tickets.recent": {
        name: "tickets.recent",
        primitive: "tickets",
        description: "Inspect recent ticket rows with show and club context.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT t.id, t.type, t.price, t.sold_out AS "soldOut",
                           s.id AS "showId", s.name AS "showName", c.name AS "clubName"
                    FROM tickets t
                    JOIN shows s ON s.id = t.show_id
                    JOIN clubs c ON c.id = s.club_id
                    WHERE t.type ILIKE ${like}
                       OR t.purchase_url ILIKE ${like}
                       OR s.name ILIKE ${like}
                       OR c.name ILIKE ${like}
                    ORDER BY t.id DESC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT t.id, t.type, t.price, t.sold_out AS "soldOut",
                       s.id AS "showId", s.name AS "showName", c.name AS "clubName"
                FROM tickets t
                JOIN shows s ON s.id = t.show_id
                JOIN clubs c ON c.id = s.club_id
                ORDER BY t.id DESC
                LIMIT ${limit}
            `;
        },
    },
    "scrapingSources.search": {
        name: "scrapingSources.search",
        primitive: "scrapingSources",
        description: "Find scraping sources with venue context.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT ss.id, ss.platform, ss.scraper_key AS "scraperKey",
                           ss.enabled, ss.priority, c.name AS "clubName"
                    FROM scraping_sources ss
                    JOIN clubs c ON c.id = ss.club_id
                    WHERE ss.scraper_key ILIKE ${like}
                       OR ss.source_url ILIKE ${like}
                       OR c.name ILIKE ${like}
                    ORDER BY ss.enabled DESC, ss.platform ASC, ss.priority ASC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT ss.id, ss.platform, ss.scraper_key AS "scraperKey",
                       ss.enabled, ss.priority, c.name AS "clubName"
                FROM scraping_sources ss
                JOIN clubs c ON c.id = ss.club_id
                ORDER BY ss.enabled DESC, ss.platform ASC, ss.priority ASC
                LIMIT ${limit}
            `;
        },
    },
    "tags.search": {
        name: "tags.search",
        primitive: "tags",
        description: "Find content tags by name, slug, type, or visibility.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT id, type, name, slug, visibility, user_facing AS "userFacing"
                    FROM tags
                    WHERE name ILIKE ${like}
                       OR slug ILIKE ${like}
                       OR type ILIKE ${like}
                       OR visibility::text ILIKE ${like}
                    ORDER BY type ASC, name ASC NULLS LAST
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT id, type, name, slug, visibility, user_facing AS "userFacing"
                FROM tags
                ORDER BY type ASC, name ASC NULLS LAST
                LIMIT ${limit}
            `;
        },
    },
    "users.search": {
        name: "users.search",
        primitive: "users",
        description: "Find users with profile role and notification settings.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT u.id, u.email, u.name, p.role, p.zip_code AS "zipCode"
                    FROM users u
                    LEFT JOIN user_profiles p ON p.user_id = u.id
                    WHERE u.email ILIKE ${like}
                       OR u.name ILIKE ${like}
                       OR p.role ILIKE ${like}
                    ORDER BY u."createdAt" DESC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT u.id, u.email, u.name, p.role, p.zip_code AS "zipCode"
                FROM users u
                LEFT JOIN user_profiles p ON p.user_id = u.id
                ORDER BY u."createdAt" DESC
                LIMIT ${limit}
            `;
        },
    },
    "podcasts.search": {
        name: "podcasts.search",
        primitive: "podcasts",
        description:
            "Find podcasts by title, author, feed, or source identifiers.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT id, slug, source, title, author_name AS "authorName",
                           last_synced_at AS "lastSyncedAt"
                    FROM podcasts
                    WHERE title ILIKE ${like}
                       OR author_name ILIKE ${like}
                       OR feed_url ILIKE ${like}
                       OR source_podcast_id ILIKE ${like}
                    ORDER BY updated_at DESC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT id, slug, source, title, author_name AS "authorName",
                       last_synced_at AS "lastSyncedAt"
                FROM podcasts
                ORDER BY updated_at DESC
                LIMIT ${limit}
            `;
        },
    },
    "emailSubscriptions.search": {
        name: "emailSubscriptions.search",
        primitive: "emailSubscriptions",
        description: "Find venue email subscription settings.",
        parameters: searchParameters,
        parseParams: parseSearchParams,
        buildQuery: ({ q, limit }: SearchParams) => {
            if (q) {
                const like = likeParam(q);
                return Prisma.sql`
                    SELECT es.id, es.sender_domain AS "senderDomain",
                           es.subscribed, es.last_received AS "lastReceived",
                           c.name AS "clubName"
                    FROM email_subscriptions es
                    JOIN clubs c ON c.id = es.club_id
                    WHERE es.sender_domain ILIKE ${like}
                       OR c.name ILIKE ${like}
                    ORDER BY es.last_received DESC NULLS LAST, c.name ASC
                    LIMIT ${limit}
                `;
            }

            return Prisma.sql`
                SELECT es.id, es.sender_domain AS "senderDomain",
                       es.subscribed, es.last_received AS "lastReceived",
                       c.name AS "clubName"
                FROM email_subscriptions es
                JOIN clubs c ON c.id = es.club_id
                ORDER BY es.last_received DESC NULLS LAST, c.name ASC
                LIMIT ${limit}
            `;
        },
    },
};

export type AdminInsightName = keyof typeof adminInsightRegistry;

export function listAdminInsights() {
    return Object.values(adminInsightRegistry).map(
        ({ name, primitive, description, parameters }) => ({
            name,
            primitive,
            description,
            parameters,
        }),
    );
}

export function getAdminInsight(name: string) {
    if (!Object.hasOwn(adminInsightRegistry, name)) {
        return null;
    }

    return adminInsightRegistry[name as AdminInsightName];
}
