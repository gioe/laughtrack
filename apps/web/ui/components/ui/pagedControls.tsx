"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from "./pagination";

interface PagedControlsProps {
    currentPage: number;
    totalPages: number;
    queryKey: string;
    className?: string;
}

const PagedControls: React.FC<PagedControlsProps> = ({
    currentPage,
    totalPages,
    queryKey,
    className,
}) => {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    if (totalPages <= 1) return null;

    const buildHref = (page: number): string => {
        const params = new URLSearchParams(searchParams?.toString() ?? "");
        if (page <= 1) {
            params.delete(queryKey);
        } else {
            params.set(queryKey, String(page));
        }
        const qs = params.toString();
        return qs ? `${pathname}?${qs}` : pathname;
    };

    const navigate = (page: number) => (e: React.MouseEvent) => {
        e.preventDefault();
        router.push(buildHref(page), { scroll: false });
    };

    const pages = buildPageWindow(currentPage, totalPages);

    return (
        <Pagination className={className}>
            <PaginationContent>
                <PaginationItem>
                    <PaginationPrevious
                        href={buildHref(Math.max(1, currentPage - 1))}
                        onClick={navigate(Math.max(1, currentPage - 1))}
                        aria-disabled={currentPage <= 1}
                        className={
                            currentPage <= 1
                                ? "pointer-events-none opacity-50"
                                : undefined
                        }
                    />
                </PaginationItem>
                {pages.map((entry, idx) =>
                    entry === "ellipsis" ? (
                        <PaginationItem key={`ellipsis-${idx}`}>
                            <PaginationEllipsis />
                        </PaginationItem>
                    ) : (
                        <PaginationItem key={entry}>
                            <PaginationLink
                                href={buildHref(entry)}
                                onClick={navigate(entry)}
                                isActive={entry === currentPage}
                            >
                                {entry}
                            </PaginationLink>
                        </PaginationItem>
                    ),
                )}
                <PaginationItem>
                    <PaginationNext
                        href={buildHref(Math.min(totalPages, currentPage + 1))}
                        onClick={navigate(Math.min(totalPages, currentPage + 1))}
                        aria-disabled={currentPage >= totalPages}
                        className={
                            currentPage >= totalPages
                                ? "pointer-events-none opacity-50"
                                : undefined
                        }
                    />
                </PaginationItem>
            </PaginationContent>
        </Pagination>
    );
};

type PageEntry = number | "ellipsis";

export function buildPageWindow(
    currentPage: number,
    totalPages: number,
): PageEntry[] {
    if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const entries: PageEntry[] = [1];
    const windowStart = Math.max(2, currentPage - 1);
    const windowEnd = Math.min(totalPages - 1, currentPage + 1);
    if (windowStart > 2) entries.push("ellipsis");
    for (let p = windowStart; p <= windowEnd; p++) entries.push(p);
    if (windowEnd < totalPages - 1) entries.push("ellipsis");
    entries.push(totalPages);
    return entries;
}

export default PagedControls;
