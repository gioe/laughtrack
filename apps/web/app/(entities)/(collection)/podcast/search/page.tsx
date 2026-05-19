import { Suspense } from "react";
import type { Metadata } from "next";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import JsonLd from "@/ui/components/JsonLd";
import SearchDetailHeader from "@/ui/pages/search/header";
import PodcastSearchClient from "@/ui/pages/search/podcast/PodcastSearchClient";
import { getSearchedPodcasts } from "@/lib/data/podcast/search/getSearchedPodcasts";
import { buildPodcastCollectionJsonLd } from "@/util/jsonLd";

type PodcastsPageProps = {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const metadata: Metadata = {
    title: "Podcasts",
    description:
        "Search comedy podcasts, hosts, and playable podcast episodes on LaughTrack.",
    alternates: {
        canonical: "/podcast/search",
    },
    openGraph: {
        title: "Podcasts | LaughTrack",
        description:
            "Search comedy podcasts, hosts, and playable podcast episodes on LaughTrack.",
        type: "website",
    },
};

function firstParam(value: string | string[] | undefined): string | undefined {
    return Array.isArray(value) ? value[0] : value;
}

export default async function PodcastsPage(props: PodcastsPageProps) {
    const searchParams = await props.searchParams;
    const q = firstParam(searchParams.q);
    const getCached = unstable_cache(
        async () => getSearchedPodcasts({ q }),
        ["podcasts-search-page-data-v2", q ?? ""],
        {
            revalidate: CACHE.search,
            tags: ["podcasts-search-page-data-v2", q ?? ""],
        },
    );
    const { data, total } = await getCached();
    const tagline = q ? `Search results for "${q}"` : "Browse comedy podcasts";

    return (
        <>
            <JsonLd data={[buildPodcastCollectionJsonLd(data)]} />
            <SearchDetailHeader
                title="Search podcasts"
                subTitle={`${total.toLocaleString("en-US")} results`}
                variant="podcast"
                tagline={tagline}
            />
            <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
                <form action="/podcast/search" className="mb-6 flex gap-2">
                    <label htmlFor="podcast-search" className="sr-only">
                        Search podcasts
                    </label>
                    <input
                        id="podcast-search"
                        name="q"
                        type="search"
                        defaultValue={q ?? ""}
                        placeholder="Search podcasts"
                        className="min-w-0 flex-1 rounded-md border border-gray-300 px-4 py-2 font-dmSans text-body text-foreground shadow-sm focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper"
                    />
                    <button
                        type="submit"
                        className="rounded-md bg-copper px-4 py-2 font-dmSans text-sm font-semibold text-white transition-colors hover:bg-copper/90 focus:outline-none focus:ring-2 focus:ring-copper"
                    >
                        Search
                    </button>
                </form>
                <Suspense>
                    <PodcastSearchClient
                        initialData={data}
                        initialTotal={total}
                    />
                </Suspense>
            </section>
        </>
    );
}
