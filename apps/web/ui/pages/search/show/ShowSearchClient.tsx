"use client";

import { useSearchParams } from "next/navigation";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { FilterDTO } from "@/objects/interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ShowTable from "@/ui/pages/search/table";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ShowSearchClientProps {
    initialData: ShowDTO[];
    initialTotal: number;
    initialFilters: FilterDTO[];
    initialZipCapTriggered?: boolean;
}

const ShowSearchClient = ({
    initialData,
    initialTotal,
    initialZipCapTriggered,
}: ShowSearchClientProps) => {
    const searchParams = useSearchParams();

    const params: Record<string, string | undefined> = {
        zip: searchParams.get("zip") ?? undefined,
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
    });

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
                <ShowTable shows={data} />
            </SearchClientShell>
        </>
    );
};

export default ShowSearchClient;
