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

    const { data, isLoading, hasMore, sentinelRef } =
        useInfiniteSearch<ComedianDTO>({
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
