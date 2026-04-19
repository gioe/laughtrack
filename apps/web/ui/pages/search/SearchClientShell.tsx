"use client";

interface SearchClientShellProps {
    isLoading: boolean;
    isError: boolean;
    errorMessage?: string | null;
    hasMore: boolean;
    dataLength: number;
    retry: () => void;
    sentinelRef: (el: Element | null) => void;
    children: React.ReactNode;
}

const SearchClientShell = ({
    isLoading,
    isError,
    errorMessage,
    hasMore,
    dataLength,
    retry,
    sentinelRef,
    children,
}: SearchClientShellProps) => {
    return (
        <>
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
