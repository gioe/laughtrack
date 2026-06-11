"use client";

import PodcastGrid from "@/ui/components/grid/podcast";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

interface PodcastSearchClientProps {
    data: PodcastDTO[];
    total: number;
}

export default function PodcastSearchClient({
    data,
    total,
}: PodcastSearchClientProps) {
    return (
        <SearchClientShell total={total}>
            <PodcastGrid podcasts={data} />
        </SearchClientShell>
    );
}
