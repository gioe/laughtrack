/**
 * @vitest-environment happy-dom
 */
import React from "react";
import {
    cleanup,
    render,
    screen,
    waitFor,
    within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import FavoritesTab from "./FavoritesTab";
import type { ShowDTO } from "@/objects/class/show/show.interface";

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
    default: ({
        show,
        variant,
    }: {
        show: ShowDTO;
        variant?: "default" | "past";
    }) => (
        <a href={`/show/${show.id}`} data-variant={variant ?? "default"}>
            {show.name}
        </a>
    ),
}));

interface MockSectionProps {
    title: string;
    items: Array<{ id?: number; uuid?: string }>;
    isLoading: boolean;
    loadError?: string | null;
    emptyMessage: string;
    renderItem: (item: never) => React.ReactNode;
    queryKey: string;
    serverPageInfo?: {
        currentPage: number;
        pageSize: number;
        totalItems: number;
    };
}

vi.mock("./FavoriteSearchableSection", () => ({
    default: ({
        title,
        items,
        isLoading,
        loadError,
        emptyMessage,
        renderItem,
        queryKey,
        serverPageInfo,
    }: MockSectionProps) => (
        <section aria-label={title}>
            <h2>{title}</h2>
            <span
                data-testid={`page-${queryKey}`}
                data-current-page={serverPageInfo?.currentPage}
                data-page-size={serverPageInfo?.pageSize}
                data-total-items={serverPageInfo?.totalItems}
            />
            {isLoading ? (
                <p role="status">Loading {title}</p>
            ) : loadError ? (
                <p role="alert">{loadError}</p>
            ) : items.length === 0 ? (
                <p>{emptyMessage}</p>
            ) : (
                items.map((item, index) => (
                    <React.Fragment
                        key={item.id ?? item.uuid ?? `item-${index}`}
                    >
                        {renderItem(item as never)}
                    </React.Fragment>
                ))
            )}
        </section>
    ),
}));

type FetchResponse = {
    ok: boolean;
    status: number;
    json: () => Promise<unknown>;
};

const jsonResponse = (body: unknown, status = 200): FetchResponse => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
});

const show = (id: number, name: string): ShowDTO => ({ id, name }) as ShowDTO;

const installFetch = ({
    upcoming = jsonResponse({ data: [], total: 0 }),
    past = jsonResponse({ data: [], total: 0 }),
    inferred = jsonResponse({ data: [], total: 0 }),
}: {
    upcoming?: FetchResponse | Promise<FetchResponse>;
    past?: FetchResponse | Promise<FetchResponse>;
    inferred?: FetchResponse | Promise<FetchResponse>;
} = {}) => {
    const fetchMock = vi.fn().mockImplementation((rawUrl: string) => {
        const url = String(rawUrl);
        if (url.startsWith("/api/v1/saved-shows?period=upcoming")) {
            return Promise.resolve(upcoming);
        }
        if (url.startsWith("/api/v1/saved-shows?period=past")) {
            return Promise.resolve(past);
        }
        if (url.startsWith("/api/v1/favorite-shows")) {
            return Promise.resolve(inferred);
        }
        return Promise.resolve(jsonResponse({ data: [] }));
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
};

beforeEach(() => {
    searchParams = new URLSearchParams();
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.resetAllMocks();
});

describe("FavoritesTab saved shows", () => {
    it("separates explicit saved shows from inferred comedian favorites", async () => {
        installFetch({
            upcoming: jsonResponse({
                data: [show(11, "Sooner"), show(12, "Later")],
                total: 2,
            }),
            past: jsonResponse({
                data: [show(9, "Last Week"), show(8, "Last Month")],
                total: 2,
            }),
            inferred: jsonResponse({
                data: [show(99, "From a Favorite Comedian")],
                total: 1,
            }),
        });

        render(<FavoritesTab />);

        const upcoming = await screen.findByRole("region", {
            name: "Saved Shows — Upcoming",
        });
        const past = await screen.findByRole("region", {
            name: "Saved Shows — Past",
        });
        expect(
            screen.getByRole("region", {
                name: "Upcoming Shows from Favorite Comedians",
            }),
        ).toBeTruthy();

        const upcomingLinks = within(upcoming).getAllByRole("link");
        expect(upcomingLinks.map((link) => link.textContent)).toEqual([
            "Sooner",
            "Later",
        ]);
        expect(upcomingLinks[0]?.getAttribute("href")).toBe("/show/11");

        const pastLinks = within(past).getAllByRole("link");
        expect(pastLinks.map((link) => link.textContent)).toEqual([
            "Last Week",
            "Last Month",
        ]);
        expect(pastLinks[0]?.getAttribute("data-variant")).toBe("past");
    });

    it("loads independent server pages for upcoming and past shows", async () => {
        searchParams = new URLSearchParams({
            upcomingSavedShowsPage: "2",
            pastSavedShowsPage: "3",
        });
        const fetchMock = installFetch({
            upcoming: jsonResponse({ data: [], total: 45 }),
            past: jsonResponse({ data: [], total: 61 }),
        });

        const { rerender } = render(<FavoritesTab />);

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/saved-shows?period=upcoming&page=2&size=20",
                { credentials: "same-origin" },
            );
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/saved-shows?period=past&page=3&size=20",
                { credentials: "same-origin" },
            );
        });
        expect(
            screen
                .getByTestId("page-upcomingSavedShowsPage")
                .getAttribute("data-current-page"),
        ).toBe("2");
        expect(
            screen
                .getByTestId("page-pastSavedShowsPage")
                .getAttribute("data-current-page"),
        ).toBe("3");

        searchParams = new URLSearchParams({
            upcomingSavedShowsPage: "4",
            pastSavedShowsPage: "1",
        });
        rerender(<FavoritesTab />);

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/saved-shows?period=upcoming&page=4&size=20",
                { credentials: "same-origin" },
            );
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/saved-shows?period=past&page=1&size=20",
                { credentials: "same-origin" },
            );
        });
    });

    it("renders loading states for both saved-show periods", () => {
        const pending = new Promise<FetchResponse>(() => {});
        installFetch({ upcoming: pending, past: pending });

        render(<FavoritesTab />);

        expect(
            within(
                screen.getByRole("region", {
                    name: "Saved Shows — Upcoming",
                }),
            ).getByRole("status").textContent,
        ).toBe("Loading Saved Shows — Upcoming");
        expect(
            within(
                screen.getByRole("region", {
                    name: "Saved Shows — Past",
                }),
            ).getByRole("status").textContent,
        ).toBe("Loading Saved Shows — Past");
    });

    it("renders distinct empty states for upcoming and past saved shows", async () => {
        installFetch();

        render(<FavoritesTab />);

        expect(
            await screen.findByText("You haven't saved any upcoming shows."),
        ).toBeTruthy();
        expect(
            screen.getByText("You haven't saved any past shows."),
        ).toBeTruthy();
    });

    it("renders independent failure states", async () => {
        installFetch({
            upcoming: jsonResponse({}, 500),
            past: jsonResponse({}, 503),
        });

        render(<FavoritesTab />);

        await waitFor(() => {
            const alerts = screen.getAllByRole("alert");
            expect(alerts.map((alert) => alert.textContent)).toEqual([
                "Failed to load upcoming saved shows.",
                "Failed to load past saved shows.",
            ]);
        });
    });
});
