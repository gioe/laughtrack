import { CACHE } from "@/util/constants/cacheConstants";
import { notFound } from "next/navigation";
import { NotFoundError } from "@/objects/NotFoundError";
import { ClosedClubError } from "@/objects/ClosedClubError";
import { auth } from "@/auth";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import SiblingLocations from "@/ui/pages/entity/club/siblings";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getClubDetailPageData } from "@/lib/data/club/detail/getClubDetailPageData";
import { unstable_cache } from "next/cache";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import { cookies } from "next/headers";
import ShowTable from "@/ui/pages/search/table";
import type { Metadata } from "next";
import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";
import JsonLd from "@/ui/components/JsonLd";
import { buildClubJsonLd, buildShowJsonLd } from "@/util/jsonLd";
import FestivalDateRange from "@/ui/pages/entity/club/festivalDateRange";

export async function generateMetadata(props: {
    params: Promise<{ name: string }>;
}): Promise<Metadata> {
    const { name: slug } = await props.params;
    const name = decodeURI(slug);

    const getClubMeta = unstable_cache(
        () =>
            db.club.findFirst({
                where: { name: { equals: name, mode: "insensitive" } },
                select: { name: true, hasImage: true, clubType: true },
            }),
        ["club-metadata", name],
        { revalidate: CACHE.detailPage, tags: ["club-metadata", name] },
    );

    const club = await getClubMeta();
    const clubName = club?.name ?? name;
    const isFestival = club?.clubType === "festival";
    const title = clubName;
    const description = isFestival
        ? `Discover the ${clubName} comedy festival. Find lineups, schedules, tickets, and more on LaughTrack.`
        : `Discover upcoming comedy shows at ${clubName}. Find schedules, tickets, and more on LaughTrack.`;
    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/club/${slug}` : undefined;
    const image = buildClubImageUrl(clubName, club?.hasImage ?? false);

    const ogTitle = `${title} | LaughTrack`;
    return {
        title,
        description,
        alternates: {
            canonical: `/club/${slug}`,
        },
        openGraph: {
            title: ogTitle,
            description,
            type: "website",
            ...(url && { url }),
            images: [{ url: image }],
        },
        twitter: { card: "summary_large_image", images: [{ url: image }] },
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
    let closedClub: { clubName: string; closedAt: Date | null } | null = null;
    try {
        result = await getCachedDetailPageData(requestData)();
    } catch (error) {
        if (error instanceof ClosedClubError) {
            closedClub = { clubName: error.clubName, closedAt: error.closedAt };
        } else if (error instanceof NotFoundError) {
            notFound();
        } else {
            throw error;
        }
    }

    if (closedClub) {
        const { clubName, closedAt } = closedClub;
        const closedDate = closedAt
            ? closedAt.toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
              })
            : null;

        return (
            <div className="max-w-7xl mx-auto px-4 py-16 text-center">
                <h1 className="text-3xl font-bold mb-4">{clubName}</h1>
                <p className="text-lg text-gray-700">
                    {clubName} has permanently closed.
                </p>
                {closedDate && (
                    <p className="mt-2 text-sm text-gray-500">
                        Closed on {closedDate}
                    </p>
                )}
                <a
                    href="/club/search"
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-copper text-white font-dmSans font-bold text-base shadow-sm hover:bg-copper/90 hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper mt-8"
                >
                    Browse other venues
                </a>
            </div>
        );
    }

    const { data, shows, total, filters, siblings } = result!;

    const isFestival = data.clubType === "festival";
    const jsonLdData = [buildClubJsonLd(data), ...shows.map(buildShowJsonLd)];

    return (
        <>
            <JsonLd data={jsonLdData} />
            <FilterModal filters={filters} total={total} />
            <ClubDetailHeader club={data} />
            {data.chainName && (
                <SiblingLocations
                    chainName={data.chainName}
                    siblings={siblings}
                />
            )}
            {isFestival && shows.length > 0 && (
                <FestivalDateRange shows={shows} />
            )}
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filterData={filters}
            />
            <ShowTable shows={shows} hideClubName />
        </>
    );
}
