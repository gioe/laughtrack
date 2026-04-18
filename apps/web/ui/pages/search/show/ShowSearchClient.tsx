"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ShowTable from "@/ui/pages/search/table";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ShowSearchClientProps {
    initialData: ShowDTO[];
    initialTotal: number;
    initialZipCapTriggered?: boolean;
}

const ShowSearchClient = ({
    initialData,
    initialTotal,
    initialZipCapTriggered,
}: ShowSearchClientProps) => {
    const searchParams = useSearchParams();
    const zip = searchParams.get("zip") ?? undefined;

    const params: Record<string, string | undefined> = {
        zip,
        distance: searchParams.get("distance") ?? undefined,
        from: searchParams.get("fromDate") ?? undefined,
        to: searchParams.get("toDate") ?? undefined,
        comedian: searchParams.get("comedian") ?? undefined,
        club: searchParams.get("club") ?? undefined,
        filters: searchParams.get("filters") ?? undefined,
        sort: searchParams.get("sort") ?? undefined,
    };

    const {
        data,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        zipCapTriggered,
        sentinelRef,
        retry,
    } = useInfiniteSearch<ShowDTO>({
        endpoint: "/api/v1/shows/search",
        params,
        initialData,
        initialTotal,
        initialZipCapTriggered,
        getItemKey: (s) => s.id,
    });

    const broadenHref = (() => {
        if (!zip) return null;
        const next = new URLSearchParams(searchParams.toString());
        next.delete("zip");
        next.delete("distance");
        const qs = next.toString();
        return qs ? `/show/search?${qs}` : "/show/search";
    })();

    const emptyAction =
        broadenHref && !isLoading ? (
            <Link
                href={broadenHref}
                className="inline-block bg-cedar text-white font-dmSans font-semibold px-6 py-3 rounded-full hover:bg-copper transition-colors"
            >
                Browse all shows
            </Link>
        ) : undefined;

    return (
        <>
            {zipCapTriggered && (
                <p className="px-4 pt-2 text-sm text-amber-700">
                    Too many locations matched. Try a more specific search like{" "}
                    <strong>&quot;City, ST&quot;</strong> for better results.
                </p>
            )}
            <SearchClientShell
                isLoading={isLoading}
                isError={isError}
                errorMessage={errorMessage}
                hasMore={hasMore}
                dataLength={data.length}
                retry={retry}
                sentinelRef={sentinelRef}
            >
                <ShowTable shows={data} emptyAction={emptyAction} />
            </SearchClientShell>
        </>
    );
};

export default ShowSearchClient;
