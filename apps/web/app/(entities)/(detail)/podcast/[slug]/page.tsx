import { notFound } from "next/navigation";
import { unstable_cache } from "next/cache";
import type { Metadata } from "next";
import { CACHE } from "@/util/constants/cacheConstants";
import { NotFoundError } from "@/objects/NotFoundError";
import { db } from "@/lib/db";
import { auth } from "@/auth";
import JsonLd from "@/ui/components/JsonLd";
import PodcastDetail from "@/ui/pages/entity/podcast";
import { getPodcastDetailPageData } from "@/lib/data/podcast/detail/getPodcastDetailPageData";
import { buildPodcastJsonLd } from "@/util/jsonLd";

export async function generateMetadata(props: {
    params: Promise<{ slug: string }>;
}): Promise<Metadata> {
    const { slug } = await props.params;
    const getPodcastMeta = unstable_cache(
        () =>
            db.podcast.findFirst({
                where: {
                    slug,
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                        },
                    },
                },
                select: {
                    title: true,
                    authorName: true,
                    description: true,
                    imageUrl: true,
                },
            }),
        ["podcast-metadata", slug],
        { revalidate: CACHE.detailPage, tags: ["podcast-metadata", slug] },
    );

    const podcast = await getPodcastMeta();
    if (!podcast) return { title: "Podcast not found" };

    const title = podcast.title;
    const description =
        podcast.description?.trim() ||
        `Listen to ${podcast.title}${podcast.authorName ? ` from ${podcast.authorName}` : ""} on LaughTrack.`;
    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/podcast/${slug}` : undefined;

    return {
        title,
        description,
        alternates: {
            canonical: `/podcast/${slug}`,
        },
        openGraph: {
            title: `${title} | LaughTrack`,
            description,
            type: "website",
            ...(url && { url }),
            ...(podcast.imageUrl && { images: [{ url: podcast.imageUrl }] }),
        },
        twitter: {
            card: "summary_large_image",
            ...(podcast.imageUrl && { images: [podcast.imageUrl] }),
        },
    };
}

export default async function PodcastDetailPage(props: {
    params: Promise<{ slug: string }>;
}) {
    const [session, { slug }] = await Promise.all([auth(), props.params]);
    const profileId = session?.profile?.id;
    const getCached = unstable_cache(
        async () => getPodcastDetailPageData(slug, profileId),
        ["podcast-detail-data-v2", slug, profileId ?? "anonymous"],
        {
            revalidate: CACHE.detailPage,
            tags: ["podcast-detail-data-v2", slug, profileId ?? "anonymous"],
        },
    );

    let result;
    try {
        result = await getCached();
    } catch (error) {
        if (error instanceof NotFoundError) {
            notFound();
        }
        throw error;
    }

    return (
        <>
            <JsonLd
                data={[buildPodcastJsonLd(result.podcast, result.episodes)]}
            />
            <PodcastDetail
                podcast={result.podcast}
                episodes={result.episodes}
                relatedComedians={result.relatedComedians}
            />
        </>
    );
}
