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
                    <span className="loading loading-spinner loading-md text-copper" />
                </div>
            )}

            {isError && (
                <div className="flex flex-col items-center gap-2 py-6">
                    <p className="text-sm text-error font-dmSans">
                        {errorMessage ?? "Failed to load results"}
                    </p>
                    <button
                        onClick={retry}
                        className="btn btn-sm btn-outline border-copper text-copper hover:bg-copper hover:text-white"
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
