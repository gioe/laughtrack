"use client";

import { useRef } from "react";
import { useSearchParams } from "next/navigation";
import PagedControls from "@/ui/components/ui/pagedControls";

// Mirrors the server-side pagination defaults (QueryHelper.getGenericClauses
// for shows/clubs/comedians, getSearchedPodcasts for podcasts): URL `page` is
// 1-based defaulting to 1, `size` defaults to 20 results per page.
export const SEARCH_PAGE_SIZE = 20;

interface SearchClientShellProps {
    total: number;
    children: React.ReactNode;
}

const SearchClientShell = ({ total, children }: SearchClientShellProps) => {
    const searchParams = useSearchParams();
    const resultsRef = useRef<HTMLDivElement>(null);

    const pageSize = Math.max(
        1,
        Number(searchParams.get("size")) || SEARCH_PAGE_SIZE,
    );
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    // Clamp like the server does, so an out-of-range ?page= URL highlights the
    // page whose results the server actually returned (the last one).
    const currentPage = Math.min(
        Math.max(1, Number(searchParams.get("page")) || 1),
        totalPages,
    );

    return (
        <>
            {/* scroll-mt clears the sticky site header (sticky top-0 py-4,
                ~72px) so post-navigation scrollIntoView doesn't tuck the
                first row of results behind it. */}
            <div ref={resultsRef} className="scroll-mt-20">
                {children}
            </div>

            {totalPages > 1 && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
                    <PagedControls
                        currentPage={currentPage}
                        totalPages={totalPages}
                        queryKey="page"
                        scrollTargetRef={resultsRef}
                    />
                </div>
            )}
        </>
    );
};

export default SearchClientShell;
