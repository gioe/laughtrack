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

    const {
        data,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        sentinelRef,
        retry,
    } = useInfiniteSearch<ShowDTO>({
        endpoint: "/api/v1/shows/search",
        params,
        initialData,
        initialTotal,
    });

    return (
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
    );
};

export default ShowSearchClient;
