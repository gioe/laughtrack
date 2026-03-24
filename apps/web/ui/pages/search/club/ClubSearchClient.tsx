"use client";

import { useSearchParams } from "next/navigation";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ClubGrid from "@/ui/components/grid/club";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface ClubSearchClientProps {
    initialData: ClubDTO[];
    initialTotal: number;
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
        <SearchClientShell
            isLoading={isLoading}
            isError={isError}
            errorMessage={errorMessage}
            hasMore={hasMore}
            dataLength={data.length}
            retry={retry}
            sentinelRef={sentinelRef}
        >
            <ClubGrid clubs={data} />
        </SearchClientShell>
    );
};

export default ClubSearchClient;
