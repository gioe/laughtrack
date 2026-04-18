import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { UserRole } from "@/objects/enum/userRole";
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { unstable_cache } from "next/cache";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import ComedianSearchClient from "@/ui/pages/search/comedian/ComedianSearchClient";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import { cookies } from "next/headers";
import { Suspense } from "react";
import type { Metadata } from "next";

export async function generateMetadata(props: {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
    const searchParams = await props.searchParams;
    const zip =
        typeof searchParams.zip === "string" ? searchParams.zip : undefined;

    const title = zip ? `Find Comedians Near ${zip}` : "Find Comedians";
    const description = zip
        ? `Browse comedy performers near ${zip}. Discover upcoming shows on LaughTrack.`
        : "Browse comedy performers and discover upcoming shows on LaughTrack.";

    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/comedian/search` : undefined;
    const ogImage = baseUrl ? `${baseUrl}/logomark-512.png` : undefined;

    const ogTitle = `${title} | LaughTrack`;
    return {
        title,
        description,
        alternates: {
            canonical: "/comedian/search",
        },
        openGraph: {
            title: ogTitle,
            description,
            type: "website",
            ...(url && { url }),
            ...(ogImage && {
                images: [
                    {
                        url: ogImage,
                        width: 512,
                        height: 512,
                        alt: "LaughTrack",
                    },
                ],
            }),
        },
        twitter: {
            card: "summary",
            ...(ogImage && { images: [ogImage] }),
        },
    };
}

interface ComedianSearchPageProps {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ComedianSearchPage(
    props: ComedianSearchPageProps,
) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const theme =
        typeof searchParams.theme === "string" ? searchParams.theme : undefined;

    const isAdmin = session?.profile?.role === UserRole.Admin;

    const requestData = {
        params: toSearchParams(searchParams),
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
        isAdmin,
    };

    const getCachedSearchPageData = (requestData: ParameterizedRequestData) => {
        return unstable_cache(
            async () => {
                try {
                    return await getSearchedComedians(requestData);
                } catch (error) {
                    console.error(
                        "Comedian search page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            ["comedian-search-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.search,
                tags: ["comedian-search-data", JSON.stringify(requestData)],
            },
        );
    };

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <>
            <FilterModal
                filters={filters}
                total={total}
                variant={SearchVariant.AllComedians}
            />

            <SearchDetailHeader
                title="Search comedians"
                subTitle={`${total} results`}
                variant="comedian"
                theme={theme}
                tagline="Find comedians performing near you"
            />

            <FilterBar
                variant={SearchVariant.AllComedians}
                total={total}
                filterData={filters}
                isAdmin={isAdmin}
            />

            <Suspense>
                <ComedianSearchClient initialData={data} initialTotal={total} />
            </Suspense>
        </>
    );
}
