import { Suspense } from "react";
import type { Metadata } from "next";
import { unstable_cache } from "next/cache";
import { auth } from "@/auth";
import { CACHE } from "@/util/constants/cacheConstants";
import JsonLd from "@/ui/components/JsonLd";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import SearchDetailHeader from "@/ui/pages/search/header";
import PodcastSearchClient from "@/ui/pages/search/podcast/PodcastSearchClient";
import { getSearchedPodcasts } from "@/lib/data/podcast/search/getSearchedPodcasts";
import { SearchVariant } from "@/objects/enum/searchVariant";
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
    const [session, searchParams] = await Promise.all([
        auth(),
        props.searchParams,
    ]);
    const q = firstParam(searchParams.q);
    const sort = firstParam(searchParams.sort);
    const includeEmpty = firstParam(searchParams.includeEmpty);
    const profileId = session?.profile?.id;
    const cacheKey = JSON.stringify({ q, sort, includeEmpty, profileId });
    const getCached = unstable_cache(
        async () => getSearchedPodcasts({ q, sort, includeEmpty, profileId }),
        ["podcasts-search-page-data-v3", cacheKey],
        {
            revalidate: CACHE.search,
            tags: ["podcasts-search-page-data-v3", cacheKey],
        },
    );
    const { data, total, filters } = await getCached();
    const tagline = q ? `Search results for "${q}"` : "Browse comedy podcasts";

    return (
        <>
            <JsonLd data={[buildPodcastCollectionJsonLd(data)]} />
            <FilterModal
                filters={filters}
                total={total}
                variant={SearchVariant.AllPodcasts}
            />
            <SearchDetailHeader
                title="Search podcasts"
                subTitle={`${total.toLocaleString("en-US")} results`}
                variant="podcast"
                tagline={tagline}
            />
            <FilterBar
                variant={SearchVariant.AllPodcasts}
                total={total}
                filterData={filters}
            />
            <Suspense>
                <PodcastSearchClient
                    initialData={data}
                    initialTotal={total}
                />
            </Suspense>
        </>
    );
}
