/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SearchClientShell from "./SearchClientShell";

const { pushMock, searchState } = vi.hoisted(() => ({
    pushMock: vi.fn(),
    searchState: { value: "" },
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ push: pushMock }),
    usePathname: () => "/show/search",
    useSearchParams: () => new URLSearchParams(searchState.value),
}));

vi.mock("@/hooks/useMotionProps", () => ({
    useMotionProps: () => ({
        prefersReducedMotion: true,
    }),
}));

const renderShell = (total: number, search = "") => {
    searchState.value = search;
    render(
        <SearchClientShell total={total}>
            <div>Result list</div>
        </SearchClientShell>,
    );
};

beforeEach(() => {
    vi.clearAllMocks();
});

afterEach(() => {
    cleanup();
});

describe("SearchClientShell", () => {
    it("renders paged controls below the list when results span multiple pages", () => {
        renderShell(414);

        const nav = screen.getByRole("navigation");
        expect(
            screen
                .getByText("Result list")
                .compareDocumentPosition(nav),
        ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
        expect(screen.getByRole("link", { name: /next/i })).toBeTruthy();
        expect(screen.getByRole("link", { name: /previous/i })).toBeTruthy();
        // 414 results at 20 per page → 21 pages; last page link is rendered.
        expect(
            screen.getByRole("link", { name: "Go to page 21" }),
        ).toBeTruthy();
    });

    it("omits paged controls when all results fit on one page", () => {
        renderShell(15);

        expect(screen.queryByRole("navigation")).toBeNull();
    });

    it("marks the page from the URL as the current page", () => {
        renderShell(100, "page=3");

        const current = screen.getByRole("link", { name: "Go to page 3" });
        expect(current.getAttribute("aria-current")).toBe("page");
    });

    it("respects a size override when computing the page count", () => {
        renderShell(100, "size=50");

        expect(
            screen.getByRole("link", { name: "Go to page 2" }),
        ).toBeTruthy();
        expect(
            screen.queryByRole("link", { name: "Go to page 3" }),
        ).toBeNull();
    });

    it("clamps an out-of-range page param to the last page", () => {
        renderShell(40, "page=99");

        const current = screen.getByRole("link", { name: "Go to page 2" });
        expect(current.getAttribute("aria-current")).toBe("page");
        expect(
            screen
                .getByRole("link", { name: /next/i })
                .getAttribute("aria-disabled"),
        ).toBe("true");
    });

    it("navigates by setting the page query param without router scroll", () => {
        renderShell(414);

        fireEvent.click(screen.getByRole("link", { name: "Go to page 2" }));

        expect(pushMock).toHaveBeenCalledWith("/show/search?page=2", {
            scroll: false,
        });
    });

    it("scrolls the results wrapper into view after page navigation", () => {
        const scrollSpy =
            vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>();
        window.HTMLElement.prototype.scrollIntoView = scrollSpy;
        renderShell(414);

        fireEvent.click(screen.getByRole("link", { name: "Go to page 2" }));

        expect(scrollSpy).toHaveBeenCalledTimes(1);
        const wrapper = scrollSpy.mock.contexts[0] as HTMLElement;
        expect(wrapper.contains(screen.getByText("Result list"))).toBe(true);
    });

    it("does not scroll when re-clicking the active page", () => {
        const scrollSpy =
            vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>();
        window.HTMLElement.prototype.scrollIntoView = scrollSpy;
        renderShell(414, "page=2");

        fireEvent.click(screen.getByRole("link", { name: "Go to page 2" }));

        expect(scrollSpy).not.toHaveBeenCalled();
    });

    it("announces the page count on the pagination landmark", () => {
        renderShell(414, "page=3");

        expect(
            screen.getByRole("navigation", {
                name: "Pagination, page 3 of 21",
            }),
        ).toBeTruthy();
    });

    it("announces and disables the previous button on the first page", () => {
        renderShell(414);

        const prev = screen.getByRole("link", { name: /previous/i });
        expect(prev.getAttribute("aria-disabled")).toBe("true");
        expect(prev.getAttribute("tabindex")).toBe("-1");

        fireEvent.click(prev);
        expect(pushMock).not.toHaveBeenCalled();
    });

    it("announces and disables the next button on the last page", () => {
        renderShell(414, "page=21");

        const next = screen.getByRole("link", { name: /next/i });
        expect(next.getAttribute("aria-disabled")).toBe("true");
        expect(next.getAttribute("tabindex")).toBe("-1");

        fireEvent.click(next);
        expect(pushMock).not.toHaveBeenCalled();
    });

    it("preserves existing filter params when navigating", () => {
        renderShell(414, "zip=10001&page=2");

        fireEvent.click(screen.getByRole("link", { name: /next/i }));

        expect(pushMock).toHaveBeenCalledWith(
            "/show/search?zip=10001&page=3",
            { scroll: false },
        );
    });

    it("drops the page param when navigating back to page 1", () => {
        renderShell(414, "page=2");

        fireEvent.click(screen.getByRole("link", { name: /previous/i }));

        expect(pushMock).toHaveBeenCalledWith("/show/search", {
            scroll: false,
        });
    });
});
