import { useCallback, useEffect, useMemo } from 'react';
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";

export function usePageParams(itemCount: number) {
    const { getTypedParam, setTypedParam } = useUrlParams();

    const page = getTypedParam(QueryProperty.Page);
    const pageSize = getTypedParam(QueryProperty.Size);

    const correctedPage = useMemo(() => {
        const maxPage = Math.ceil(itemCount / pageSize);
        // The pagination library we're using is zero indexed but our pagination is not.
        // We keep one-based indexing in the URL for better user experience.
        return Math.min(page, maxPage) - 1;
    }, [itemCount, page, pageSize]);

    // Update URL if we need to correct the page number
    useEffect(() => {
        if (correctedPage !== page - 1) {
            setTypedParam(QueryProperty.Page, correctedPage + 1);
        }
    }, [correctedPage, page, setTypedParam]);

    const updatePage = useCallback((newPageIndex: number) => {
        setTypedParam(QueryProperty.Page, newPageIndex + 1);
    }, [setTypedParam]);

    const updatePageSize = useCallback((newSize: number) => {
        setTypedParam(QueryProperty.Size, newSize);
    }, [setTypedParam]);

    return {
        currentPage: correctedPage,
        pageSize,
        updatePage,
        updatePageSize
    };
}
