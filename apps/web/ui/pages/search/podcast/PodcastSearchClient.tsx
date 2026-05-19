"use client";

import { useSearchParams } from "next/navigation";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import PodcastGrid from "@/ui/components/grid/podcast";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

interface PodcastSearchClientProps {
    initialData: PodcastDTO[];
    initialTotal: number;
}

export default function PodcastSearchClient({
    initialData,
    initialTotal,
}: PodcastSearchClientProps) {
    const searchParams = useSearchParams();
    const params = {
        q: searchParams.get("q") ?? undefined,
        sort: searchParams.get("sort") ?? undefined,
    };
    const {
        data,
        total,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        sentinelRef,
        loadMore,
        retry,
    } = useInfiniteSearch<PodcastDTO>({
        endpoint: "/api/v1/podcasts/search",
        params,
        initialData,
        initialTotal,
        getItemKey: (podcast) => podcast.id,
    });

    return (
        <SearchClientShell
            isLoading={isLoading}
            isError={isError}
            errorMessage={errorMessage}
            hasMore={hasMore}
            dataLength={data.length}
            total={total}
            loadMore={loadMore}
            retry={retry}
            sentinelRef={sentinelRef}
        >
            <PodcastGrid podcasts={data} />
        </SearchClientShell>
    );
}
