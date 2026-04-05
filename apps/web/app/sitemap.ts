import type { MetadataRoute } from "next";
import { db } from "@/lib/db";

const SITE_URL = "https://www.laugh-track.com";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const [clubs, comedians] = await Promise.all([
        db.club.findMany({
            where: { visible: true },
            select: { name: true },
            orderBy: { popularity: "desc" },
        }),
        db.comedian.findMany({
            where: { totalShows: { gt: 0 } },
            select: { name: true },
            orderBy: { popularity: "desc" },
        }),
    ]);

    const staticPages: MetadataRoute.Sitemap = [
        { url: SITE_URL, changeFrequency: "daily", priority: 1.0 },
        {
            url: `${SITE_URL}/show/search`,
            changeFrequency: "daily",
            priority: 0.9,
        },
        {
            url: `${SITE_URL}/club/search`,
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${SITE_URL}/comedian/search`,
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${SITE_URL}/about`,
            changeFrequency: "monthly",
            priority: 0.3,
        },
        {
            url: `${SITE_URL}/privacy`,
            changeFrequency: "monthly",
            priority: 0.2,
        },
        {
            url: `${SITE_URL}/terms`,
            changeFrequency: "monthly",
            priority: 0.2,
        },
    ];

    const clubPages: MetadataRoute.Sitemap = clubs.map((club) => ({
        url: `${SITE_URL}/club/${encodeURIComponent(club.name)}`,
        changeFrequency: "daily" as const,
        priority: 0.7,
    }));

    const comedianPages: MetadataRoute.Sitemap = comedians.map((comedian) => ({
        url: `${SITE_URL}/comedian/${encodeURIComponent(comedian.name)}`,
        changeFrequency: "weekly" as const,
        priority: 0.6,
    }));

    return [...staticPages, ...clubPages, ...comedianPages];
}
