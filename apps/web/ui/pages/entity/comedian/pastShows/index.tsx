"use client";

import { ShowDTO } from "@/objects/class/show/show.interface";
import { useInfiniteSearch } from "@/hooks/useInfiniteSearch";
import ShowCard, { ShowCardContext } from "@/ui/components/cards/show";

interface PastShowsSectionProps {
    shows?: ShowDTO[];
    total?: number;
    comedianName: string;
    showCardContext?: ShowCardContext;
}

const PAGE_SIZE = 20;

const PastShowsSection = ({
    shows = [],
    total = 0,
    comedianName,
    showCardContext,
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
            <h2 className="font-urbanist-bold text-h2 font-bold text-foreground">
                Past Shows
            </h2>
            <p className="text-muted-foreground font-dmSans text-body mb-8">
                {liveTotal} past {liveTotal === 1 ? "show" : "shows"}
            </p>
            <div className="grid grid-cols-1 gap-y-6 sm:gap-y-8 md:gap-y-10">
                {data.map((show) => (
                    <ShowCard
                        key={show.id}
                        show={show}
                        variant="past"
                        context={showCardContext}
                    />
                ))}
            </div>

            {isLoading && (
                <div className="flex justify-center py-6">
                    <span
                        role="status"
                        aria-label="Loading"
                        className="inline-block w-6 h-6 border-2 border-copper border-t-transparent rounded-full animate-spin"
                    />
                </div>
            )}

            {isError && (
                <div className="flex flex-col items-center gap-2 py-6">
                    <p className="text-sm text-red-600 font-dmSans">
                        {errorMessage ?? "Failed to load results"}
                    </p>
                    <button
                        onClick={retry}
                        className="inline-flex items-center justify-center px-3 py-1 text-xs border border-copper text-copper rounded-md hover:bg-copper hover:text-white transition-colors"
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
            <div
                ref={sentinelRef as (el: HTMLDivElement | null) => void}
                className="h-4"
                aria-hidden="true"
            />
        </section>
    );
};

export default PastShowsSection;
