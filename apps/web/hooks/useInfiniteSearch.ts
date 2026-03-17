"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface UseInfiniteSearchOptions<T> {
    endpoint: string;
    /** Filter/sort params (excluding page/size). When these change, results reset to page 0. */
    params: Record<string, string | undefined>;
    initialData: T[];
    initialTotal: number;
    pageSize?: number;
}

interface UseInfiniteSearchResult<T> {
    data: T[];
    total: number;
    isLoading: boolean;
    isError: boolean;
    errorMessage?: string;
    hasMore: boolean;
    /** Attach this ref to the sentinel div at the bottom of the list. */
    sentinelRef: (el: Element | null) => void;
    /** Re-triggers loadMore from the current page after an error. */
    retry: () => void;
}

export function useInfiniteSearch<T>({
    endpoint,
    params,
    initialData,
    initialTotal,
    pageSize = 25,
}: UseInfiniteSearchOptions<T>): UseInfiniteSearchResult<T> {
    const paramsKey = JSON.stringify(params);
    const prevParamsKey = useRef(paramsKey);

    const [data, setData] = useState<T[]>(initialData);
    const [total, setTotal] = useState(initialTotal);
    const [isLoading, setIsLoading] = useState(false);
    const [isError, setIsError] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | undefined>(
        undefined,
    );
    const [hasMore, setHasMore] = useState(initialData.length < initialTotal);

    // Refs avoid stale closure issues inside the observer callback
    const nextPageRef = useRef(1); // page 0 already served by SSR
    const loadedCountRef = useRef(initialData.length);
    const isLoadingRef = useRef(false);
    const paramsRef = useRef(params);
    paramsRef.current = params;

    const observerRef = useRef<IntersectionObserver | null>(null);

    const loadMore = useCallback(async () => {
        if (isLoadingRef.current) return;

        isLoadingRef.current = true;
        setIsLoading(true);

        const page = nextPageRef.current;

        try {
            const query = new URLSearchParams();
            Object.entries(paramsRef.current).forEach(([k, v]) => {
                if (v !== undefined && v !== "") query.set(k, v);
            });
            query.set("page", String(page));
            query.set("size", String(pageSize));

            const res = await fetch(`${endpoint}?${query.toString()}`);
            if (!res.ok) throw new Error(`${res.status}`);

            const json = (await res.json()) as { data: T[]; total: number };

            const newCount =
                page === 0
                    ? json.data.length
                    : loadedCountRef.current + json.data.length;

            setData((prev) =>
                page === 0 ? json.data : [...prev, ...json.data],
            );
            setTotal(json.total);
            setHasMore(newCount < json.total);
            setIsError(false);
            setErrorMessage(undefined);

            loadedCountRef.current = newCount;
            nextPageRef.current = page + 1;
        } catch (err) {
            console.error("useInfiniteSearch fetch error:", err);
            setIsError(true);
            setErrorMessage(
                err instanceof Error ? err.message : "Failed to load results",
            );
        } finally {
            isLoadingRef.current = false;
            setIsLoading(false);
        }
    }, [endpoint, pageSize]);

    // When params change (sort/filter/search-text), reset to page 0
    useEffect(() => {
        if (paramsKey === prevParamsKey.current) return;
        prevParamsKey.current = paramsKey;

        nextPageRef.current = 0;
        loadedCountRef.current = 0;
        setData([]);
        setTotal(0);
        setHasMore(true);

        loadMore();
    }, [paramsKey, loadMore]);

    // IntersectionObserver sentinel ref
    const sentinelRef = useCallback(
        (el: Element | null) => {
            observerRef.current?.disconnect();
            observerRef.current = null;
            if (!el) return;

            observerRef.current = new IntersectionObserver(
                (entries) => {
                    if (entries[0]?.isIntersecting) {
                        loadMore();
                    }
                },
                { rootMargin: "200px" },
            );
            observerRef.current.observe(el);
        },
        [loadMore],
    );

    return {
        data,
        total,
        isLoading,
        isError,
        errorMessage,
        hasMore,
        sentinelRef,
        retry: loadMore,
    };
}
