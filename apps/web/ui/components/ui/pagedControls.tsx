"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
// Direct module import (not the @/hooks barrel): the barrel transitively
// pulls next-auth via sibling hooks, which breaks node-environment unit
// tests that import this file for buildPageWindow.
import { useMotionProps } from "@/hooks/useMotionProps";
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
    // Opt-in: scroll this element to the top of the viewport after page
    // navigation. Consumers that paginate mid-page (e.g. the profile's
    // FavoriteSearchableSection) omit it to stay in place instead of
    // jumping past their surrounding content.
    scrollTargetRef?: React.RefObject<HTMLElement | null>;
}

const PagedControls: React.FC<PagedControlsProps> = ({
    currentPage,
    totalPages,
    queryKey,
    className,
    scrollTargetRef,
}) => {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const { prefersReducedMotion } = useMotionProps();

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

    const navigate =
        (page: number, disabled = false) =>
        (e: React.MouseEvent) => {
            e.preventDefault();
            if (disabled) return;
            router.push(buildHref(page), { scroll: false });
            // Re-clicking the active page replaces the URL with itself; the
            // content doesn't change, so don't yank the viewport around.
            if (page !== currentPage) {
                scrollTargetRef?.current?.scrollIntoView({
                    behavior: prefersReducedMotion ? "auto" : "smooth",
                    block: "start",
                });
            }
        };

    const pages = buildPageWindow(currentPage, totalPages);
    const prevDisabled = currentPage <= 1;
    const nextDisabled = currentPage >= totalPages;

    return (
        <Pagination
            className={className}
            aria-label={`Pagination, page ${currentPage} of ${totalPages}`}
        >
            <PaginationContent>
                <PaginationItem>
                    <PaginationPrevious
                        href={buildHref(Math.max(1, currentPage - 1))}
                        onClick={navigate(
                            Math.max(1, currentPage - 1),
                            prevDisabled,
                        )}
                        aria-disabled={prevDisabled}
                        tabIndex={prevDisabled ? -1 : undefined}
                        className={
                            prevDisabled
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
                                aria-label={`Go to page ${entry}`}
                            >
                                {entry}
                            </PaginationLink>
                        </PaginationItem>
                    ),
                )}
                <PaginationItem>
                    <PaginationNext
                        href={buildHref(Math.min(totalPages, currentPage + 1))}
                        onClick={navigate(
                            Math.min(totalPages, currentPage + 1),
                            nextDisabled,
                        )}
                        aria-disabled={nextDisabled}
                        tabIndex={nextDisabled ? -1 : undefined}
                        className={
                            nextDisabled
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
