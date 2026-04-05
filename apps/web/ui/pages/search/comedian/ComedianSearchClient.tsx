"use client";

import { useSearchParams } from "next/navigation";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ComedianSearchClientProps {
    initialData: ComedianDTO[];
    initialTotal: number;
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
        includeEmpty: searchParams.get("includeEmpty") ?? undefined,
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
        <SearchClientShell
            isLoading={isLoading}
            isError={isError}
            errorMessage={errorMessage}
            hasMore={hasMore}
            dataLength={data.length}
            retry={retry}
            sentinelRef={sentinelRef}
        >
            <ComedianGrid
                comedians={data}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
            />
        </SearchClientShell>
    );
};

export default ComedianSearchClient;
