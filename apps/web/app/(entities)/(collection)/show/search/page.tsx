import { auth } from "@/auth";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowSearchClient from "@/ui/pages/search/show/ShowSearchClient";
import FilterModal from "@/ui/components/modals/filter";
import { cookies } from "next/headers";
import { Suspense } from "react";
import type { Metadata } from "next";

export async function generateMetadata(props: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
    const searchParams = await props.searchParams;
    const comedian =
        typeof searchParams.comedian === "string"
            ? searchParams.comedian
            : undefined;
    const zip =
        typeof searchParams.zip === "string" ? searchParams.zip : undefined;

    let titleBase = "Comedy Shows";
    if (comedian && zip) titleBase = `${comedian} Shows Near ${zip}`;
    else if (comedian) titleBase = `${comedian} Shows`;
    else if (zip) titleBase = `Comedy Shows Near ${zip}`;

    const title = `${titleBase} | LaughTrack`;
    const description = comedian
        ? `Find upcoming ${comedian} comedy shows. Browse schedules, tickets, and more on LaughTrack.`
        : zip
          ? `Discover upcoming comedy shows near ${zip}. Browse schedules, tickets, and more on LaughTrack.`
          : "Discover upcoming comedy shows. Browse schedules, tickets, and more on LaughTrack.";

    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/show/search` : undefined;

    return {
        title,
        description,
        openGraph: {
            title,
            description,
            type: "website",
            ...(url && { url }),
        },
    };
}

export default async function ShowSearchPage(props: any) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const requestData = {
        params: toSearchParams(searchParams),
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
    };

    const getCachedSearchPageData = (requestData: ParameterizedRequestData) =>
        unstable_cache(
            async () => {
                try {
                    return await getSearchedShows(requestData);
                } catch (error) {
                    console.error("Show search page data fetch error:", error);
                    throw error;
                }
            },
            ["show-search-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.search,
                tags: ["show-search-data", JSON.stringify(requestData)],
            },
        );

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <>
            <FilterModal filters={filters} total={total} />
            <FilterBar
                variant={SearchVariant.AllShows}
                total={total}
                filters={filters.length}
            />
            <Suspense>
                <ShowSearchClient
                    initialData={data}
                    initialTotal={total}
                    initialFilters={filters}
                />
            </Suspense>
        </>
    );
}
