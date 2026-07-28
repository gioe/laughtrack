/**
 * @vitest-environment happy-dom
 */
import React from "react";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ShowDetailHeader from "./index";
import type { ShowDetailDTO } from "@/lib/data/show/detail/interface";

const { mockLoginOpen, mockUseSession } = vi.hoisted(() => ({
    mockLoginOpen: vi.fn(),
    mockUseSession: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
}));

vi.mock("@/hooks/useLoginModal", () => ({
    default: () => ({
        isOpen: false,
        onOpen: mockLoginOpen,
        onClose: vi.fn(),
    }),
}));

vi.mock("next/link", () => ({
    default: ({
        children,
        href,
    }: {
        children: React.ReactNode;
        href: string;
    }) => <a href={href}>{children}</a>,
}));

vi.mock("@/ui/pages/entity/MarqueeHero", () => ({
    default: ({
        title,
        children,
    }: {
        title: string;
        children?: React.ReactNode;
    }) => (
        <section>
            <h1>{title}</h1>
            {children}
        </section>
    ),
}));

const show: ShowDetailDTO = {
    id: 42,
    clubId: 24,
    date: "2026-08-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
    showPageUrl: "https://example.com/show",
};

const response = (body: unknown, status = 200): Response =>
    ({
        ok: status >= 200 && status < 300,
        status,
        json: vi.fn().mockResolvedValue(body),
    }) as unknown as Response;

const authenticatedSession = {
    status: "authenticated",
    data: { user: { id: "user-1" } },
    update: vi.fn(),
};

beforeEach(() => {
    mockUseSession.mockReturnValue(authenticatedSession);
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
});

describe("ShowDetailHeader saved-show action", () => {
    it("disables saving at the exact show start boundary", async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-08-28T19:59:30Z"));
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: false } }));
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        const saveButton = screen.getByRole("button", {
            name: "Save show",
        });
        expect(saveButton).toHaveProperty("disabled", false);

        await act(async () => {
            vi.advanceTimersByTime(30_001);
        });

        expect(saveButton).toHaveProperty("disabled", true);
        fireEvent.click(saveButton);
        expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("does not offer an enabled save action after the show starts", async () => {
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: false } }));
        vi.stubGlobal("fetch", mockFetch);
        const startedShow = {
            ...show,
            date: new Date(Date.now() - 30 * 60 * 1000) as never as Date,
        };

        render(<ShowDetailHeader show={startedShow} />);

        const saveButton = await screen.findByRole("button", {
            name: "Save show",
        });
        expect(saveButton).toHaveProperty("disabled", true);
        fireEvent.click(saveButton);
        expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("still removes a saved show after it starts without allowing it to be saved again", async () => {
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: true } }))
            .mockResolvedValueOnce(response({ data: { isSaved: false } }));
        vi.stubGlobal("fetch", mockFetch);
        const startedShow = {
            ...show,
            date: new Date(Date.now() - 30 * 60 * 1000) as never as Date,
        };

        render(<ShowDetailHeader show={startedShow} />);

        const removeButton = await screen.findByRole("button", {
            name: "Remove saved show",
        });
        expect(removeButton).toHaveProperty("disabled", false);
        fireEvent.click(removeButton);

        const saveButton = await screen.findByRole("button", {
            name: "Save show",
        });
        expect(saveButton).toHaveProperty("disabled", true);
        expect(mockFetch).toHaveBeenNthCalledWith(2, "/api/v1/saved-shows/42", {
            method: "DELETE",
        });
    });

    it("saves and unsaves a show without reloading the page", async () => {
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: false } }))
            .mockResolvedValueOnce(response({ data: { isSaved: true } }))
            .mockResolvedValueOnce(response({ data: { isSaved: false } }));
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);

        const saveButton = await screen.findByRole("button", {
            name: "Save show",
        });
        expect(saveButton.getAttribute("aria-pressed")).toBe("false");

        fireEvent.click(saveButton);
        const removeButton = await screen.findByRole("button", {
            name: "Remove saved show",
        });
        expect(removeButton.getAttribute("aria-pressed")).toBe("true");

        fireEvent.click(removeButton);
        await screen.findByRole("button", { name: "Save show" });

        expect(mockFetch).toHaveBeenNthCalledWith(
            1,
            "/api/v1/saved-shows/42",
            expect.objectContaining({ method: "GET" }),
        );
        expect(mockFetch).toHaveBeenNthCalledWith(2, "/api/v1/saved-shows/42", {
            method: "POST",
        });
        expect(mockFetch).toHaveBeenNthCalledWith(3, "/api/v1/saved-shows/42", {
            method: "DELETE",
        });
    });

    it("opens authentication for signed-out visitors without fetching", () => {
        mockUseSession.mockReturnValue({
            status: "unauthenticated",
            data: null,
            update: vi.fn(),
        });
        const mockFetch = vi.fn();
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);
        fireEvent.click(
            screen.getByRole("button", {
                name: "Sign in to save this show",
            }),
        );

        expect(mockLoginOpen).toHaveBeenCalledTimes(1);
        expect(mockFetch).not.toHaveBeenCalled();
    });

    it("announces pending and successful mutations", async () => {
        let resolveMutation!: (value: Response) => void;
        const pendingMutation = new Promise<Response>((resolve) => {
            resolveMutation = resolve;
        });
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: false } }))
            .mockReturnValueOnce(pendingMutation);
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);
        fireEvent.click(
            await screen.findByRole("button", { name: "Save show" }),
        );

        const pendingButton = screen.getByRole("button", {
            name: "Saving show…",
        });
        expect(pendingButton.getAttribute("aria-busy")).toBe("true");
        expect(pendingButton).toHaveProperty("disabled", true);

        await act(async () => {
            resolveMutation(response({ data: { isSaved: true } }));
            await pendingMutation;
        });

        expect((await screen.findByRole("status")).textContent).toBe(
            "Show saved.",
        );
        expect(
            screen
                .getByRole("button", { name: "Remove saved show" })
                .getAttribute("aria-pressed"),
        ).toBe("true");
    });

    it("preserves pressed state and exposes API failures as alerts", async () => {
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: true } }))
            .mockResolvedValueOnce(
                response({ error: "Unable to remove saved show" }, 500),
            );
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);
        fireEvent.click(
            await screen.findByRole("button", {
                name: "Remove saved show",
            }),
        );

        expect((await screen.findByRole("alert")).textContent).toBe(
            "Unable to remove saved show",
        );
        await waitFor(() => {
            expect(
                screen
                    .getByRole("button", {
                        name: "Remove saved show",
                    })
                    .getAttribute("aria-pressed"),
            ).toBe("true");
        });
    });

    it("does not claim an unsaved state when the initial read fails", async () => {
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(
                response({ error: "Unable to load saved show" }, 500),
            );
        vi.stubGlobal("fetch", mockFetch);

        render(<ShowDetailHeader show={show} />);

        expect((await screen.findByRole("alert")).textContent).toBe(
            "Unable to load saved show",
        );
        const unavailableButton = screen.getByRole("button", {
            name: "Saved show status unavailable",
        });
        expect(unavailableButton.getAttribute("aria-pressed")).toBeNull();
        expect(unavailableButton).toHaveProperty("disabled", true);
    });

    it("ignores a mutation result after navigating to another show", async () => {
        let resolveMutation!: (value: Response) => void;
        const pendingMutation = new Promise<Response>((resolve) => {
            resolveMutation = resolve;
        });
        const mockFetch = vi
            .fn()
            .mockResolvedValueOnce(response({ data: { isSaved: false } }))
            .mockReturnValueOnce(pendingMutation)
            .mockResolvedValueOnce(response({ data: { isSaved: false } }));
        vi.stubGlobal("fetch", mockFetch);

        const { rerender } = render(<ShowDetailHeader show={show} />);
        fireEvent.click(
            await screen.findByRole("button", { name: "Save show" }),
        );

        rerender(
            <ShowDetailHeader
                show={{
                    ...show,
                    id: 43,
                    name: "Next Show",
                }}
            />,
        );
        await screen.findByRole("button", { name: "Save show" });

        await act(async () => {
            resolveMutation(response({ data: { isSaved: true } }));
            await pendingMutation;
        });

        await waitFor(() => {
            expect(
                screen.getByRole("button", { name: "Save show" }),
            ).toBeTruthy();
            expect(screen.queryByRole("status")).toBeNull();
        });
    });
});
