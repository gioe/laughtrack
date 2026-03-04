import { CACHE } from "@/util/constants/cacheConstants";
import { notFound } from "next/navigation";
import { auth } from "@/auth";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getClubDetailPageData } from "@/lib/data/club/detail/getClubDetailPageData";
import { unstable_cache } from "next/cache";
import { ParameterizedRequestData } from "@/objects/interface";
import { cookies } from "next/headers";
import ShowTable from "@/ui/pages/search/table";
import type { Metadata } from "next";
import { db } from "@/lib/db";

export async function generateMetadata(props: {
    params: Promise<{ name: string }>;
}): Promise<Metadata> {
    const { name: slug } = await props.params;
    const name = decodeURI(slug);

    const getClubName = unstable_cache(
        () =>
            db.club.findFirst({
                where: { name: { equals: name, mode: "insensitive" } },
                select: { name: true },
            }),
        ["club-metadata", name],
        { revalidate: CACHE.detailPage, tags: ["club-metadata", name] },
    );

    const club = await getClubName();
    const clubName = club?.name ?? name;
    const title = `${clubName} | LaughTrack`;
    const description = `Discover upcoming comedy shows at ${clubName}. Find schedules, tickets, and more on LaughTrack.`;

    return {
        title,
        description,
        openGraph: { title, description },
    };
}

export default async function ClubDetailPage(props: {
    searchParams: Promise<any>;
    params: Promise<{ name: string }> | undefined;
}) {
    const [session, cookieStore, searchParams, slug] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
        props.params,
    ]);

    const requestData = {
        params: searchParams,
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
        slug: slug?.name,
    };

    const getCachedDetailPageData = (requestData: ParameterizedRequestData) =>
        unstable_cache(
            async () => {
                try {
                    return await getClubDetailPageData(requestData);
                } catch (error) {
                    console.error("Club detail page data fetch error:", error);
                    throw error;
                }
            },
            ["club-detail-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.detailPage,
                tags: ["club-detail-data", JSON.stringify(requestData)],
            },
        );

    let result;
    try {
        result = await getCachedDetailPageData(requestData)();
    } catch (error) {
        if (error instanceof Error && /not found/i.test(error.message)) {
            notFound();
        }
        throw error;
    }

    const { data, shows, total, filters } = result;

    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <FilterModal filters={filters} total={total} />
            <ClubDetailHeader club={data} />
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filters={filters.length > 0}
            />
            <ShowTable shows={shows} />
        </main>
    );
}
