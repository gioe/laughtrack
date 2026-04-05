import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import SearchDetailHeader from "@/ui/pages/search/header";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getSearchedClubs } from "@/lib/data/club/search/getSearchedClubs";
import { unstable_cache } from "next/cache";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import ClubSearchClient from "@/ui/pages/search/club/ClubSearchClient";
import { cookies } from "next/headers";
import { Suspense } from "react";
import type { Metadata } from "next";

export async function generateMetadata(props: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
    const searchParams = await props.searchParams;
    const zip =
        typeof searchParams.zip === "string" ? searchParams.zip : undefined;

    const title = zip ? `Comedy Clubs Near ${zip}` : "Comedy Clubs";
    const description = zip
        ? `Find comedy clubs near ${zip}. Discover shows and venues on LaughTrack.`
        : "Find comedy clubs near you. Discover shows and venues on LaughTrack.";

    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/club/search` : undefined;

    const ogTitle = `${title} | LaughTrack`;
    return {
        title,
        description,
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

interface ClubSearchPageProps {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ClubSearchPage(props: ClubSearchPageProps) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const theme =
        typeof searchParams.theme === "string" ? searchParams.theme : undefined;

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
                    return await getSearchedClubs(requestData);
                } catch (error) {
                    console.error("Club search page data fetch error:", error);
                    throw error;
                }
            },
            ["club-search-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.search,
                tags: ["club-search-data", JSON.stringify(requestData)],
            },
        );

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <>
            <FilterModal filters={filters} total={total} />
            <SearchDetailHeader
                title="Search clubs"
                subTitle={`${total} results`}
                variant="club"
                theme={theme}
                tagline="Discover comedy clubs in your area"
            />
            <FilterBar
                variant={SearchVariant.AllClubs}
                total={total}
                filterData={filters}
            />
            <Suspense>
                <ClubSearchClient initialData={data} initialTotal={total} />
            </Suspense>
        </>
    );
}
