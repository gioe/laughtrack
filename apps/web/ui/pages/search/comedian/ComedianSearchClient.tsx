"use client";

import { useSearchParams } from "next/navigation";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { FilterDTO } from "@/objects/interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ComedianGrid from "@/ui/components/grid/comedian";

interface ComedianSearchClientProps {
    initialData: ComedianDTO[];
    initialTotal: number;
    initialFilters: FilterDTO[];
}

const ComedianSearchClient = ({
    initialData,
    initialTotal,
}: ComedianSearchClientProps) => {
    const searchParams = useSearchParams();

    const params: Record<string, string | undefined> = {
        comedian: searchParams.get("comedian") ?? undefined,
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
    } = useInfiniteSearch<ComedianDTO>({
        endpoint: "/api/v1/comedians/search",
        params,
        initialData,
        initialTotal,
    });

    return (
        <>
            <ComedianGrid
                comedians={data}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
            />

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

export default ComedianSearchClient;
