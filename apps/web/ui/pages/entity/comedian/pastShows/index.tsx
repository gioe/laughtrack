"use client";

import { ShowDTO } from "@/objects/class/show/show.interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ShowCard from "@/ui/components/cards/show";
import SearchClientShell from "@/ui/pages/search/SearchClientShell";

interface PastShowsSectionProps {
    shows?: ShowDTO[];
    total?: number;
    comedianName: string;
}

const PAGE_SIZE = 20;

const PastShowsSection = ({
    shows = [],
    total = 0,
    comedianName,
}: PastShowsSectionProps) => {
    const {
        data,
        total: liveTotal,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        sentinelRef,
        retry,
    } = useInfiniteSearch<ShowDTO>({
        endpoint: "/api/v1/comedians/past-shows",
        params: { comedian: comedianName },
        initialData: shows,
        initialTotal: total,
        pageSize: PAGE_SIZE,
        fetchInitialPage: shows.length === 0 && total === 0,
        getItemKey: (s) => s.id,
    });

    if (!isLoading && liveTotal === 0) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10 mb-10">
            <h2 className="font-gilroy-bold text-h2 font-bold text-cedar">
                Past Shows
            </h2>
            <p className="text-gray-600 font-dmSans text-body mb-8">
                {liveTotal} past {liveTotal === 1 ? "show" : "shows"}
            </p>
            <SearchClientShell
                isLoading={isLoading}
                isError={isError}
                errorMessage={errorMessage}
                hasMore={hasMore}
                dataLength={data.length}
                retry={retry}
                sentinelRef={sentinelRef}
            >
                <div className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10">
                    {data.map((show) => (
                        <ShowCard key={show.id} show={show} variant="past" />
                    ))}
                </div>
            </SearchClientShell>
        </section>
    );
};

export default PastShowsSection;
