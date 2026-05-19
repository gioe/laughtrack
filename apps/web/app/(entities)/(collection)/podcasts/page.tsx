import { Suspense } from "react";
import type { Metadata } from "next";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import JsonLd from "@/ui/components/JsonLd";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterBar from "@/ui/pages/search/filterBar";
import PodcastSearchClient from "@/ui/pages/search/podcast/PodcastSearchClient";
import { getSearchedPodcasts } from "@/lib/data/podcast/search/getSearchedPodcasts";
import { buildPodcastCollectionJsonLd } from "@/util/jsonLd";
import { SearchVariant } from "@/objects/enum/searchVariant";

type PodcastsPageProps = {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const metadata: Metadata = {
    title: "Podcasts",
    description:
        "Search comedy podcasts, hosts, and playable podcast episodes on LaughTrack.",
    alternates: {
        canonical: "/podcasts",
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
    const sort = firstParam(searchParams.sort);
    const getCached = unstable_cache(
        async () => getSearchedPodcasts({ q, sort }),
        ["podcasts-search-page-data-v3", q ?? "", sort ?? ""],
        {
            revalidate: CACHE.search,
            tags: ["podcasts-search-page-data-v3", q ?? "", sort ?? ""],
        },
    );
    const { data, total } = await getCached();
    const tagline = q ? `Search results for "${q}"` : "Browse comedy podcasts";

    return (
        <>
            <JsonLd data={[buildPodcastCollectionJsonLd(data)]} />
            <SearchDetailHeader
                title="Search podcasts"
                subTitle={`${total} results`}
                variant="podcast"
                tagline={tagline}
            />
            <FilterBar
                variant={SearchVariant.AllPodcasts}
                total={total}
                filterData={[]}
            />
            <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
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
