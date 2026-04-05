import { auth } from "@/auth";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import SearchDetailHeader from "@/ui/pages/search/header";
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
    const club =
        typeof searchParams.club === "string" ? searchParams.club : undefined;
    const fromDate =
        typeof searchParams.fromDate === "string"
            ? searchParams.fromDate
            : undefined;
    const toDate =
        typeof searchParams.toDate === "string"
            ? searchParams.toDate
            : undefined;

    let titleBase = "Comedy Shows";
    if (comedian && club && zip)
        titleBase = `${comedian} Shows at ${club} Near ${zip}`;
    else if (comedian && club) titleBase = `${comedian} Shows at ${club}`;
    else if (comedian && zip) titleBase = `${comedian} Shows Near ${zip}`;
    else if (comedian) titleBase = `${comedian} Shows`;
    else if (club && zip) titleBase = `${club} Shows Near ${zip}`;
    else if (club) titleBase = `${club} Shows`;
    else if (zip) titleBase = `Comedy Shows Near ${zip}`;

    const title = titleBase;

    let dateContext = "";
    if (fromDate && toDate) dateContext = ` from ${fromDate} to ${toDate}`;
    else if (fromDate) dateContext = ` from ${fromDate}`;
    else if (toDate) dateContext = ` through ${toDate}`;

    const description = comedian
        ? `Find upcoming ${comedian} comedy shows${dateContext}. Browse schedules, tickets, and more on LaughTrack.`
        : club
          ? `Discover upcoming comedy shows at ${club}${dateContext}. Browse schedules, tickets, and more on LaughTrack.`
          : zip
            ? `Discover upcoming comedy shows near ${zip}${dateContext}. Browse schedules, tickets, and more on LaughTrack.`
            : `Discover upcoming comedy shows${dateContext}. Browse schedules, tickets, and more on LaughTrack.`;

    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/show/search` : undefined;

    const ogTitle = `${title} | LaughTrack`;
    return {
        title,
        description,
        alternates: {
            canonical: "/show/search",
        },
        openGraph: {
            title: ogTitle,
            description,
            type: "website",
            ...(url && { url }),
        },
        twitter: {
            card: "summary",
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

    const { data, total, filters, zipCapTriggered } =
        await getCachedSearchPageData(requestData)();

    return (
        <>
            <FilterModal filters={filters} total={total} />

            <SearchDetailHeader
                title="Search shows"
                subTitle={`${total} results`}
                variant="show"
                tagline="Find upcoming comedy shows near you"
            />

            <FilterBar
                variant={SearchVariant.AllShows}
                total={total}
                filterData={filters}
            />
            <Suspense>
                <ShowSearchClient
                    initialData={data}
                    initialTotal={total}
                    initialZipCapTriggered={zipCapTriggered}
                />
            </Suspense>
        </>
    );
}
