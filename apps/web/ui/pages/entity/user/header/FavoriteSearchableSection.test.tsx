/**
 * @vitest-environment happy-dom
 */
import React from "react";
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    vi,
} from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import FavoriteSearchableSection from "./FavoriteSearchableSection";

let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useSearchParams: () => searchParams,
    useRouter: () => ({ push: vi.fn() }),
    usePathname: () => "/user/me",
}));

interface Item {
    id: number;
    label: string;
}

const makeItems = (n: number, prefix = "Item"): Item[] =>
    Array.from({ length: n }, (_, i) => ({
        id: i + 1,
        label: `${prefix} ${i + 1}`,
    }));

const renderItem = (item: Item) => (
    <div data-testid={`item-${item.id}`}>{item.label}</div>
);
const itemKey = (item: Item) => item.id;
const matchesQuery = (item: Item, q: string) =>
    item.label.toLowerCase().includes(q);

describe("FavoriteSearchableSection serverPageInfo branch", () => {
    beforeEach(() => {
        searchParams = new URLSearchParams();
    });

    afterEach(() => {
        cleanup();
    });

    it("renders all server-supplied items without client slicing", () => {
        const items = makeItems(20);
        render(
            <FavoriteSearchableSection<Item>
                title="Shows"
                items={items}
                isLoading={false}
                emptyMessage="empty"
                searchPlaceholder="search"
                matchesQuery={matchesQuery}
                renderItem={renderItem}
                itemKey={itemKey}
                gridClassName="grid"
                queryKey="showsPage"
                serverPageInfo={{
                    currentPage: 3,
                    pageSize: 20,
                    totalItems: 137,
                }}
            />,
        );

        for (let i = 1; i <= 20; i++) {
            expect(screen.getByTestId(`item-${i}`)).toBeTruthy();
        }
    });

    it("derives totalPages from serverPageInfo.totalItems / pageSize", () => {
        const items = makeItems(20);
        render(
            <FavoriteSearchableSection<Item>
                title="Shows"
                items={items}
                isLoading={false}
                emptyMessage="empty"
                searchPlaceholder="search"
                matchesQuery={matchesQuery}
                renderItem={renderItem}
                itemKey={itemKey}
                gridClassName="grid"
                queryKey="showsPage"
                serverPageInfo={{
                    currentPage: 3,
                    pageSize: 20,
                    totalItems: 137,
                }}
            />,
        );

        // ceil(137 / 20) = 7. The pagination should show the last page (7).
        const lastPageLink = screen.getByRole("link", { name: /^7$/ });
        expect(lastPageLink).toBeTruthy();
    });

    it("clamps currentPage to totalPages when the requested page is past the end", () => {
        const items = makeItems(20);
        render(
            <FavoriteSearchableSection<Item>
                title="Shows"
                items={items}
                isLoading={false}
                emptyMessage="empty"
                searchPlaceholder="search"
                matchesQuery={matchesQuery}
                renderItem={renderItem}
                itemKey={itemKey}
                gridClassName="grid"
                queryKey="showsPage"
                serverPageInfo={{
                    currentPage: 999,
                    pageSize: 20,
                    totalItems: 60,
                }}
            />,
        );

        // totalPages = 3; current page should clamp to 3 and be marked active.
        const activeLink = screen
            .getAllByRole("link")
            .find((el) => el.getAttribute("aria-current") === "page");
        expect(activeLink?.textContent).toBe("3");
    });

    it("falls back to client-side pagination when serverPageInfo is absent", () => {
        // 25 items, default PAGE_SIZE=20, so the first page shows items 1..20.
        const items = makeItems(25);
        render(
            <FavoriteSearchableSection<Item>
                title="Shows"
                items={items}
                isLoading={false}
                emptyMessage="empty"
                searchPlaceholder="search"
                matchesQuery={matchesQuery}
                renderItem={renderItem}
                itemKey={itemKey}
                gridClassName="grid"
                queryKey="showsPage"
            />,
        );

        expect(screen.getByTestId("item-1")).toBeTruthy();
        expect(screen.getByTestId("item-20")).toBeTruthy();
        expect(screen.queryByTestId("item-21")).toBeNull();
    });
});
