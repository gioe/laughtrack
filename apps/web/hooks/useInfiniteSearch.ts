"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface UseInfiniteSearchOptions<T> {
    endpoint: string;
    /** Filter/sort params (excluding page/size). When these change, results reset to page 0. */
    params: Record<string, string | undefined>;
    initialData: T[];
    initialTotal: number;
    pageSize?: number;
    initialZipCapTriggered?: boolean;
    /**
     * Optional extractor for a stable item key. When provided, merged pages are deduped
     * by this key so the same entity can't appear twice if the server returns it on
     * multiple pages (e.g. when a non-strict sort drifts an item across a page boundary).
     */
    getItemKey?: (item: T) => string | number;
}

interface UseInfiniteSearchResult<T> {
    data: T[];
    total: number;
    isLoading: boolean;
    isError: boolean;
    errorMessage?: string;
    hasMore: boolean;
    zipCapTriggered: boolean;
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
    initialZipCapTriggered = false,
    getItemKey,
}: UseInfiniteSearchOptions<T>): UseInfiniteSearchResult<T> {
    const getItemKeyRef = useRef(getItemKey);
    getItemKeyRef.current = getItemKey;
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
    const [zipCapTriggered, setZipCapTriggered] = useState(
        initialZipCapTriggered,
    );

    // Refs avoid stale closure issues inside the observer callback
    const nextPageRef = useRef(1); // page 0 already served by SSR
    const loadedCountRef = useRef(initialData.length);
    const isLoadingRef = useRef(false);
    const hasMoreRef = useRef(initialData.length < initialTotal);
    const paramsRef = useRef(params);
    paramsRef.current = params;

    const observerRef = useRef<IntersectionObserver | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const loadMore = useCallback(async () => {
        if (!hasMoreRef.current) return;
        if (isLoadingRef.current) return;

        isLoadingRef.current = true;
        setIsLoading(true);

        const page = nextPageRef.current;
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            const query = new URLSearchParams();
            Object.entries(paramsRef.current).forEach(([k, v]) => {
                if (v !== undefined && v !== "") query.set(k, v);
            });
            query.set("page", String(page));
            query.set("size", String(pageSize));

            const res = await fetch(`${endpoint}?${query.toString()}`, {
                signal: controller.signal,
            });
            if (!res.ok) throw new Error(`${res.status}`);

            const json = (await res.json()) as {
                data: T[];
                total: number;
                zipCapTriggered?: boolean;
            };

            const newCount =
                page === 0
                    ? json.data.length
                    : loadedCountRef.current + json.data.length;

            setData((prev) => {
                const keyFn = getItemKeyRef.current;
                if (!keyFn) {
                    return page === 0 ? json.data : [...prev, ...json.data];
                }
                const base = page === 0 ? [] : prev;
                const seen = new Set<string | number>();
                for (const item of base) seen.add(keyFn(item));
                const merged = [...base];
                for (const item of json.data) {
                    const k = keyFn(item);
                    if (seen.has(k)) continue;
                    seen.add(k);
                    merged.push(item);
                }
                return merged;
            });
            setTotal(json.total);
            hasMoreRef.current = newCount < json.total;
            setHasMore(newCount < json.total);
            setZipCapTriggered(json.zipCapTriggered ?? false);
            setIsError(false);
            setErrorMessage(undefined);

            loadedCountRef.current = newCount;
            nextPageRef.current = page + 1;
        } catch (err) {
            if (err instanceof Error && err.name === "AbortError") return;
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

        abortControllerRef.current?.abort();

        nextPageRef.current = 0;
        loadedCountRef.current = 0;
        hasMoreRef.current = true;
        setData([]);
        setTotal(0);
        setHasMore(true);
        setZipCapTriggered(false);

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
        zipCapTriggered,
        sentinelRef,
        retry: loadMore,
    };
}
