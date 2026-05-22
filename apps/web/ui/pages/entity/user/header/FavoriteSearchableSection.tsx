"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, Search } from "lucide-react";
import PagedControls from "@/ui/components/ui/pagedControls";

export const PAGE_SIZE = 20;

export interface ServerPageInfo {
    currentPage: number;
    pageSize: number;
    totalItems: number;
}

export interface FavoriteSearchableSectionProps<T> {
    title: string;
    items: T[];
    isLoading: boolean;
    loadError?: string | null;
    emptyMessage: string;
    searchPlaceholder: string;
    matchesQuery: (item: T, query: string) => boolean;
    renderItem: (item: T) => React.ReactNode;
    itemKey: (item: T) => string | number;
    gridClassName: string;
    queryKey: string;
    headerNote?: React.ReactNode;
    serverPageInfo?: ServerPageInfo;
}

function FavoriteSearchableSection<T>({
    title,
    items,
    isLoading,
    loadError,
    emptyMessage,
    searchPlaceholder,
    matchesQuery,
    renderItem,
    itemKey,
    gridClassName,
    queryKey,
    headerNote,
    serverPageInfo,
}: FavoriteSearchableSectionProps<T>) {
    const [search, setSearch] = React.useState("");
    const searchParams = useSearchParams();
    const pageFromUrl = Math.max(
        1,
        Number.parseInt(searchParams?.get(queryKey) ?? "1", 10) || 1,
    );

    const normalizedQuery = search.trim().toLowerCase();
    const filtered = React.useMemo(() => {
        if (!normalizedQuery) return items;
        return items.filter((item) => matchesQuery(item, normalizedQuery));
    }, [items, normalizedQuery, matchesQuery]);

    let totalPages: number;
    let currentPage: number;
    let pagedItems: T[];
    if (serverPageInfo) {
        // Server already returned a single page; only filter within that page.
        const pageSize = serverPageInfo.pageSize;
        totalPages = Math.max(
            1,
            Math.ceil(serverPageInfo.totalItems / pageSize),
        );
        currentPage = Math.min(
            Math.max(1, serverPageInfo.currentPage),
            totalPages,
        );
        pagedItems = filtered;
    } else {
        totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
        currentPage = Math.min(pageFromUrl, totalPages);
        pagedItems = filtered.slice(
            (currentPage - 1) * PAGE_SIZE,
            currentPage * PAGE_SIZE,
        );
    }

    return (
        <section className="space-y-4">
            <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="font-gilroy-bold text-h2 font-extrabold text-foreground">
                    {title}
                </h2>
                {headerNote ? (
                    <div className="font-dmSans text-xs text-gray-500">
                        {headerNote}
                    </div>
                ) : null}
            </header>

            <div className="relative">
                <Search
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
                />
                <input
                    type="search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={searchPlaceholder}
                    aria-label={`Search ${title}`}
                    className="w-full rounded-full border border-gray-200 bg-white py-2 pl-9 pr-3 font-dmSans text-sm text-foreground placeholder:text-gray-400 focus:border-copper focus:outline-none focus:ring-1 focus:ring-copper"
                />
            </div>

            {isLoading ? (
                <div className="flex justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-copper" />
                </div>
            ) : loadError ? (
                <p className="py-12 text-center font-dmSans text-sm text-red-600">
                    {loadError}
                </p>
            ) : items.length === 0 ? (
                <p className="py-12 text-center font-dmSans text-sm text-gray-500">
                    {emptyMessage}
                </p>
            ) : filtered.length === 0 ? (
                <p className="py-12 text-center font-dmSans text-sm text-gray-500">
                    No matches for &ldquo;{search.trim()}&rdquo;.
                </p>
            ) : (
                <>
                    <div className={gridClassName}>
                        {pagedItems.map((item) => (
                            <React.Fragment key={itemKey(item)}>
                                {renderItem(item)}
                            </React.Fragment>
                        ))}
                    </div>
                    <PagedControls
                        currentPage={currentPage}
                        totalPages={totalPages}
                        queryKey={queryKey}
                        className="pt-2"
                    />
                </>
            )}
        </section>
    );
}

export default FavoriteSearchableSection;
