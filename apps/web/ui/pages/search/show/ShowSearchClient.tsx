"use client";

import { useSearchParams } from "next/navigation";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { FilterDTO } from "@/objects/interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ShowTable from "@/ui/pages/search/table";

interface ShowSearchClientProps {
    initialData: ShowDTO[];
    initialTotal: number;
    initialFilters: FilterDTO[];
}

const ShowSearchClient = ({
    initialData,
    initialTotal,
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

    const { data, isLoading, hasMore, sentinelRef } =
        useInfiniteSearch<ShowDTO>({
            endpoint: "/api/v1/shows/search",
            params,
            initialData,
            initialTotal,
        });

    return (
        <>
            <ShowTable shows={data} />

            {/* Sentinel div — IntersectionObserver triggers next page load */}
            <div ref={sentinelRef} className="h-4" aria-hidden="true" />

            {isLoading && (
                <div className="flex justify-center py-6">
                    <span className="loading loading-spinner loading-md text-copper" />
                </div>
            )}

            {!hasMore && data.length > 0 && (
                <p className="text-center text-sm text-copper/60 py-4 font-dmSans">
                    All results loaded
                </p>
            )}
        </>
    );
};

export default ShowSearchClient;
