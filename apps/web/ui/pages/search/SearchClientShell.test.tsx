/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SearchClientShell from "./SearchClientShell";

afterEach(() => {
    cleanup();
});

const renderShell = ({
    hasMore = true,
    dataLength = 20,
    total = 414,
    loadMore = vi.fn(),
}: {
    hasMore?: boolean;
    dataLength?: number;
    total?: number;
    loadMore?: () => void;
} = {}) => {
    const retry = vi.fn();
    const sentinelRef = vi.fn();

    render(
        <SearchClientShell
            isLoading={false}
            isError={false}
            hasMore={hasMore}
            dataLength={dataLength}
            total={total}
            loadMore={loadMore}
            retry={retry}
            sentinelRef={sentinelRef}
        >
            <div>Result list</div>
        </SearchClientShell>,
    );

    return { loadMore, retry, sentinelRef };
};

describe("SearchClientShell", () => {
    it("renders the result count in chip-style chrome before the list", () => {
        renderShell();

        const summary = screen.getByText("Showing 20 of 414");
        expect(summary.closest("div")?.className).toContain("rounded-full");
        expect(summary.compareDocumentPosition(screen.getByText("Result list")))
            .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });

    it("renders an above-list load more button when more results exist", () => {
        const loadMore = vi.fn();
        renderShell({ loadMore });

        fireEvent.click(screen.getByRole("button", { name: "Load more" }));

        expect(loadMore).toHaveBeenCalledTimes(1);
    });

    it("omits the above-list load more button when all results are loaded", () => {
        renderShell({ hasMore: false, dataLength: 25, total: 25 });

        expect(
            screen.queryByRole("button", { name: "Load more" }),
        ).toBeNull();
        expect(screen.getByText("All results loaded")).toBeTruthy();
    });
});
