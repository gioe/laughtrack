"use client";

import { useSearchParams } from "next/navigation";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { FilterDTO } from "@/objects/interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ClubGrid from "@/ui/components/grid/club";

interface ClubSearchClientProps {
    initialData: ClubDTO[];
    initialTotal: number;
    initialFilters: FilterDTO[];
}

const ClubSearchClient = ({
    initialData,
    initialTotal,
}: ClubSearchClientProps) => {
    const searchParams = useSearchParams();

    const params: Record<string, string | undefined> = {
        club: searchParams.get("club") ?? undefined,
        sort: searchParams.get("sort") ?? undefined,
        filters: searchParams.get("filters") ?? undefined,
    };

    const {
        data,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        sentinelRef,
        retry,
    } = useInfiniteSearch<ClubDTO>({
        endpoint: "/api/v1/clubs/search",
        params,
        initialData,
        initialTotal,
    });

    return (
        <>
            <ClubGrid clubs={data} />

            {isLoading && (
                <div className="flex justify-center py-6">
                    <span className="loading loading-spinner loading-md text-copper" />
                </div>
            )}

            {isError && (
                <div className="flex flex-col items-center gap-2 py-6">
                    <p className="text-sm text-error font-dmSans">
                        {errorMessage ?? "Failed to load results"}
                    </p>
                    <button
                        onClick={retry}
                        className="btn btn-sm btn-outline border-copper text-copper hover:bg-copper hover:text-white"
                    >
                        Retry
                    </button>
                </div>
            )}

            {!hasMore && data.length > 0 && (
                <p className="text-center text-sm text-copper/60 py-4 font-dmSans">
                    All results loaded
                </p>
            )}

            {/* Sentinel div — IntersectionObserver triggers next page load */}
            <div ref={sentinelRef} className="h-4" aria-hidden="true" />
        </>
    );
};

export default ClubSearchClient;
