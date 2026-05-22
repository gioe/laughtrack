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
import { cleanup, render, waitFor } from "@testing-library/react";
import FavoritesTab from "./FavoritesTab";

let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useSearchParams: () => searchParams,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
    usePathname: () => "/user/me",
}));

vi.mock("@/ui/components/cards/comedian", () => ({
    default: () => <div data-testid="comedian-card" />,
}));
vi.mock("@/ui/components/cards/club/search", () => ({
    default: () => <div data-testid="club-card" />,
}));
vi.mock("@/ui/components/cards/podcast", () => ({
    default: () => <div data-testid="podcast-card" />,
}));
vi.mock("@/ui/components/cards/show", () => ({
    default: () => <div data-testid="show-card" />,
}));
vi.mock("./FavoriteSearchableSection", () => ({
    default: ({ title, items }: { title: string; items: unknown[] }) => (
        <div data-testid={`section-${title}`} data-count={items.length} />
    ),
}));

type FetchResponse = {
    ok: boolean;
    status: number;
    json: () => Promise<unknown>;
};
const jsonResponse = (body: unknown): FetchResponse => ({
    ok: true,
    status: 200,
    json: async () => body,
});

describe("FavoritesTab shows pagination", () => {
    let fetchMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        searchParams = new URLSearchParams();
        fetchMock = vi.fn().mockImplementation((url: string) => {
            if (url.startsWith("/api/v1/favorite-shows")) {
                return Promise.resolve(
                    jsonResponse({ data: [], total: 137, page: 1, size: 20 }),
                );
            }
            return Promise.resolve(jsonResponse({ data: [] }));
        });
        vi.stubGlobal("fetch", fetchMock);
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
        vi.resetAllMocks();
    });

    const favoriteShowsCalls = (): string[] =>
        fetchMock.mock.calls
            .map((args) => String(args[0]))
            .filter((u) => u.startsWith("/api/v1/favorite-shows"));

    it("requests page=1 with size=20 on initial mount", async () => {
        render(<FavoritesTab userId="user-1" />);

        await waitFor(() => {
            expect(favoriteShowsCalls()).toContain(
                "/api/v1/favorite-shows?page=1&size=20",
            );
        });
    });

    it("refetches with the new page when showsPage URL param changes", async () => {
        const { rerender } = render(<FavoritesTab userId="user-1" />);

        await waitFor(() => {
            expect(favoriteShowsCalls()).toContain(
                "/api/v1/favorite-shows?page=1&size=20",
            );
        });

        searchParams = new URLSearchParams({ showsPage: "3" });
        rerender(<FavoritesTab userId="user-1" />);

        await waitFor(() => {
            expect(favoriteShowsCalls()).toContain(
                "/api/v1/favorite-shows?page=3&size=20",
            );
        });
    });

    it.each([
        ["non-numeric", "not-a-number"],
        ["zero", "0"],
        ["negative", "-3"],
    ])(
        "clamps %s showsPage value (%s) to page=1",
        async (_label, raw) => {
            searchParams = new URLSearchParams({ showsPage: raw });
            render(<FavoritesTab userId="user-1" />);

            await waitFor(() => {
                expect(favoriteShowsCalls()).toContain(
                    "/api/v1/favorite-shows?page=1&size=20",
                );
            });

            const otherPageHits = favoriteShowsCalls().filter(
                (u) => !u.endsWith("?page=1&size=20"),
            );
            expect(otherPageHits).toEqual([]);
        },
    );
});
