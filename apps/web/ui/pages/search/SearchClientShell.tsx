"use client";

import { searchFilterChipCompactClassName } from "@/ui/components/params/search/filterChipStyles";

interface SearchClientShellProps {
    isLoading: boolean;
    isError: boolean;
    errorMessage?: string | null;
    hasMore: boolean;
    dataLength: number;
    total?: number;
    loadMore?: () => void;
    retry: () => void;
    sentinelRef: (el: Element | null) => void;
    children: React.ReactNode;
}

const formatCount = (count: number) => count.toLocaleString("en-US");

const SearchClientShell = ({
    isLoading,
    isError,
    errorMessage,
    hasMore,
    dataLength,
    total,
    loadMore,
    retry,
    sentinelRef,
    children,
}: SearchClientShellProps) => {
    const showSummary = typeof total === "number" && dataLength > 0;
    const summaryTotal = total ?? dataLength;
    const canLoadMore = hasMore && !!loadMore;

    return (
        <>
            {showSummary && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-4 pb-2">
                    <div
                        className={`${searchFilterChipCompactClassName} w-fit max-w-full flex-wrap border-white/10 text-white/85`}
                    >
                        <span>
                            Showing {formatCount(dataLength)} of{" "}
                            {formatCount(summaryTotal)}
                        </span>
                        {canLoadMore && (
                            <>
                                <span
                                    aria-hidden="true"
                                    className="text-white/35"
                                >
                                    &middot;
                                </span>
                                <button
                                    type="button"
                                    onClick={loadMore}
                                    disabled={isLoading}
                                    className="font-bold text-copper transition-colors hover:text-copper/80 focus:outline-none disabled:cursor-not-allowed disabled:text-white/40"
                                >
                                    Load more
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}

            {children}

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

            {!hasMore && dataLength > 0 && (
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
        </>
    );
};

export default SearchClientShell;
