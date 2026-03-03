import { useCallback, useEffect, useMemo } from 'react';
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";

export function usePageParams(itemCount: number) {
    const { getTypedParam, setTypedParam, setMultipleTypedParams } = useUrlParams();

    // Get current values from URL, defaulting to 1 for page and 10 for size
    const page = Number(getTypedParam(QueryProperty.Page)) || 1;
    const pageSize = Number(getTypedParam(QueryProperty.Size)) || 10;

    // Calculate the maximum valid page number
    const maxPage = Math.max(1, Math.ceil(itemCount / pageSize));

    // Ensure page is within valid bounds (1 to maxPage)
    const correctedPage = useMemo(() => {
        return Math.min(Math.max(1, page), maxPage);
    }, [page, maxPage]);

    // Update URL if we need to correct the page number
    useEffect(() => {
        if (correctedPage !== page) {
            setTypedParam(QueryProperty.Page, correctedPage);
        }
    }, [correctedPage, page, setTypedParam]);

    // Convert to zero-based index for internal use
    const zeroBasedPage = correctedPage - 1;

    const updatePage = useCallback((newPageIndex: number) => {
        // Convert from zero-based to one-based for URL
        setTypedParam(QueryProperty.Page, newPageIndex + 1);
    }, [setTypedParam]);

    const updatePageSize = useCallback((newSize: number) => {

        setTypedParam(QueryProperty.Size, newSize);
        // Reset to page 1 when changing page size
        setMultipleTypedParams({
            page: 1,
            size: newSize
        });
    }, [setMultipleTypedParams]);

    return {
        currentPage: zeroBasedPage,
        pageSize,
        updatePage,
        updatePageSize
    };
}
