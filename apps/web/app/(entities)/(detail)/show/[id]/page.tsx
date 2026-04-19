import { CACHE } from "@/util/constants/cacheConstants";
import { notFound } from "next/navigation";
import { NotFoundError } from "@/objects/NotFoundError";
import { unstable_cache } from "next/cache";
import { getShowDetailPageData } from "@/lib/data/show/detail/getShowDetailPageData";
import { db } from "@/lib/db";
import { formatShowDate } from "@/util/dateUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import JsonLd from "@/ui/components/JsonLd";
import { buildShowJsonLd } from "@/util/jsonLd";
import type { Metadata } from "next";
import ShowDetailHeader from "@/ui/pages/entity/show/header";
import ShowLineupSection from "@/ui/pages/entity/show/lineupSection";
import ShowTicketCta from "@/ui/pages/entity/show/ticketCta";
import ShowDescription from "@/ui/pages/entity/show/description";
import RelatedShowsSection from "@/ui/pages/entity/show/relatedShows";

function parseShowId(raw: string): number | null {
    const id = Number(raw);
    if (!Number.isInteger(id) || id <= 0) return null;
    return id;
}

export async function generateMetadata(props: {
    params: Promise<{ id: string }>;
}): Promise<Metadata> {
    const { id: rawId } = await props.params;
    const id = parseShowId(rawId);
    if (!id) return { title: "Show not found" };

    const getShowMeta = unstable_cache(
        () =>
            db.show.findUnique({
                where: { id },
                select: {
                    name: true,
                    date: true,
                    club: {
                        select: {
                            name: true,
                            hasImage: true,
                            timezone: true,
                            visible: true,
                        },
                    },
                },
            }),
        ["show-metadata", String(id)],
        { revalidate: CACHE.detailPage, tags: ["show-metadata", String(id)] },
    );

    const row = await getShowMeta();
    if (!row || !row.club.visible) {
        return { title: "Show not found" };
    }

    const clubName = row.club.name;
    const showTitle = row.name?.trim() || `Comedy at ${clubName}`;
    const dateLabel = formatShowDate(row.date.toISOString(), row.club.timezone);
    const title = `${showTitle} · ${clubName} · ${dateLabel}`;
    const description = `${showTitle} at ${clubName} on ${dateLabel}. Lineup and ticket info on LaughTrack.`;
    const baseUrl = process.env.NEXT_PUBLIC_WEBSITE_URL;
    const url = baseUrl ? `${baseUrl}/show/${id}` : undefined;
    const image = buildClubImageUrl(clubName, row.club.hasImage);

    return {
        title,
        description,
        alternates: {
            canonical: `/show/${id}`,
        },
        openGraph: {
            title: `${showTitle} | LaughTrack`,
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

export default async function ShowDetailPage(props: {
    params: Promise<{ id: string }>;
}) {
    const { id: rawId } = await props.params;
    const id = parseShowId(rawId);
    if (!id) notFound();

    const getCached = unstable_cache(
        async () => getShowDetailPageData(id),
        ["show-detail-data", String(id)],
        {
            revalidate: CACHE.detailPage,
            tags: ["show-detail-data", String(id)],
        },
    );

    let result;
    try {
        result = await getCached();
    } catch (error) {
        if (error instanceof NotFoundError) {
            notFound();
        }
        throw error;
    }

    const { show, relatedShows } = result;
    const jsonLdData = [buildShowJsonLd(show)];

    return (
        <>
            <JsonLd data={jsonLdData} />
            <ShowDetailHeader show={show} />
            <ShowTicketCta show={show} />
            <ShowDescription description={show.description} />
            <ShowLineupSection lineup={show.lineup ?? []} />
            <RelatedShowsSection
                shows={relatedShows}
                clubName={show.clubName}
                clubSlug={show.clubSlug}
            />
        </>
    );
}
