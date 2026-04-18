import { CACHE } from "@/util/constants/cacheConstants";
import { notFound } from "next/navigation";
import { NotFoundError } from "@/objects/NotFoundError";
import { auth } from "@/auth";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getComedianDetailPageData } from "@/lib/data/comedian/detail/getComedianDetailPageData";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/header";
import PastShowsSection from "@/ui/pages/entity/comedian/pastShows";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { cookies } from "next/headers";
import ShowTable from "@/ui/pages/search/table";
import type { Metadata } from "next";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import JsonLd from "@/ui/components/JsonLd";
import { buildComedianJsonLd, buildShowJsonLd } from "@/util/jsonLd";

export async function generateMetadata(props: {
    params: Promise<{ name: string }>;
}): Promise<Metadata> {
    const { name: slug } = await props.params;
    const name = decodeURI(slug);

    const getComedianName = unstable_cache(
        () =>
            db.comedian.findFirst({
                where: { name: { equals: name, mode: "insensitive" } },
                select: { name: true, hasImage: true },
            }),
        ["comedian-metadata", name],
        { revalidate: CACHE.detailPage, tags: ["comedian-metadata", name] },
    );

    const comedian = await getComedianName();
    const comedianName = comedian?.name ?? name;
    const title = comedianName;
    const description = `Discover upcoming comedy shows featuring ${comedianName}. Find schedules, tickets, and more on LaughTrack.`;
    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/comedian/${slug}` : undefined;
    const image = buildComedianImageUrl(
        comedianName,
        comedian?.hasImage ?? false,
    );

    const ogTitle = `${title} | LaughTrack`;
    return {
        title,
        description,
        alternates: {
            canonical: `/comedian/${slug}`,
        },
        openGraph: {
            title: ogTitle,
            description,
            type: "website",
            ...(url && { url }),
            ...(image && { images: [{ url: image }] }),
        },
        twitter: {
            card: "summary_large_image",
            ...(image && { images: [{ url: image }] }),
        },
    };
}

export default async function ComedianDetailsPage(props: {
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
        params: toSearchParams(searchParams),
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
        slug: slug?.name,
    };

    const getCachedDetailPageData = (requestData: ParameterizedRequestData) =>
        unstable_cache(
            async () => {
                try {
                    return await getComedianDetailPageData(requestData);
                } catch (error) {
                    console.error(
                        "Comedian detail page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            ["comedian-detail-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.detailPage,
                tags: ["comedian-detail-data", JSON.stringify(requestData)],
            },
        );

    let result;
    try {
        result = await getCachedDetailPageData(requestData)();
    } catch (error) {
        if (error instanceof NotFoundError) {
            notFound();
        }
        throw error;
    }

    const { data, shows, total, pastShows, pastShowsTotal, filters } = result;

    const jsonLdData = [
        buildComedianJsonLd(data),
        ...shows.map(buildShowJsonLd),
    ];

    return (
        <>
            <JsonLd data={jsonLdData} />
            <FilterModal filters={filters} total={total} />
            <ComedianDetailHeader comedian={data} />
            <FilterBar
                variant={SearchVariant.ComedianDetail}
                total={total}
                filterData={filters}
            />
            <ShowTable shows={shows} />
            <PastShowsSection shows={pastShows} total={pastShowsTotal} />
        </>
    );
}
