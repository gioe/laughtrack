import { CACHE } from "@/util/constants/cacheConstants";
import { notFound } from "next/navigation";
import { NotFoundError } from "@/objects/NotFoundError";
import { ClosedClubError } from "@/objects/ClosedClubError";
import { auth } from "@/auth";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
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
    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/club/${slug}` : undefined;
    const image = buildClubImageUrl(clubName);

    return {
        title,
        description,
        openGraph: {
            title,
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
                <p className="text-lg text-base-content/70">
                    {clubName} has permanently closed.
                </p>
                {closedDate && (
                    <p className="mt-2 text-sm text-base-content/50">
                        Closed on {closedDate}
                    </p>
                )}
                <a href="/club/search" className="btn btn-primary mt-8">
                    Browse other venues
                </a>
            </div>
        );
    }

    const { data, shows, total, filters } = result!;

    return (
        <>
            <FilterModal filters={filters} total={total} />
            <ClubDetailHeader club={data} />
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filters={filters.length}
            />
            <ShowTable shows={shows} />
        </>
    );
}
