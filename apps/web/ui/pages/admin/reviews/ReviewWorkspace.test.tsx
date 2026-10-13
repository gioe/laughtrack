/** @vitest-environment happy-dom */
import {
    cleanup,
    render,
    screen,
    fireEvent,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import ReviewWorkspace from "./ReviewWorkspace";
const mocks = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../shared/adminRequest", () => ({ adminRequest: mocks.request }));
vi.mock("next/link", () => ({
    default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
}));
const item = {
    id: "a",
    workflow: "comedian_identity",
    title: "Robin Tran",
    subtitle: "Identity review",
    status: "pending",
    token: "token",
    matches: [{ id: 9, name: "Robin Tran" }],
    evidence: [
        {
            id: "e",
            title: "Friday comedy",
            context: "Featuring Robin Tran",
            source: "Venue website",
            kind: "extracted_lineup",
            url: "https://example.com",
            showId: 1,
        },
    ],
    history: [],
};
beforeEach(() => {
    mocks.request.mockReset();
    mocks.request.mockImplementation(
        async (url: string, init?: RequestInit) => {
            if (init?.method === "POST") return { decisionId: "decision" };
            if (url.includes("id=")) return item;
            return {
                items: [item, { ...item, id: "b", title: "Another Person" }],
                total: 2,
                page: 1,
            };
        },
    );
});
afterEach(cleanup);
it("loads evidence in place and links the selected canonical profile", async () => {
    render(<ReviewWorkspace />);
    await screen.findByText("Featuring Robin Tran");
    fireEvent.click(screen.getByRole("button", { name: "Robin Tran" }));
    fireEvent.click(screen.getByLabelText("Also confirm this show appearance"));
    fireEvent.click(screen.getByRole("button", { name: "Link existing" }));
    await waitFor(() =>
        expect(mocks.request).toHaveBeenCalledWith(
            "/api/admin/reviews",
            expect.objectContaining({ method: "POST" }),
        ),
    );
    const call = mocks.request.mock.calls.find(
        ([, init]) => init?.method === "POST",
    )!;
    expect(JSON.parse(call[1].body)).toMatchObject({
        action: "link",
        targetId: 9,
        showIds: [1],
        token: "token",
    });
    expect(
        await screen.findByRole("button", { name: "Undo last decision" }),
    ).toBeTruthy();
});
it("skip advances without posting a decision", async () => {
    render(<ReviewWorkspace />);
    await screen.findByText("Featuring Robin Tran");
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await screen.findByRole("button", { name: /Return to skipped items/ });
    expect(
        mocks.request.mock.calls.some(([, init]) => init?.method === "POST"),
    ).toBe(false);
});
it("shows failed decisions and keeps evidence available", async () => {
    mocks.request.mockImplementation(
        async (url: string, init?: RequestInit) => {
            if (init?.method === "POST")
                throw new Error(
                    "This item changed. Refresh it before deciding.",
                );
            if (url.includes("id=")) return item;
            return { items: [item], total: 1, page: 1 };
        },
    );
    render(<ReviewWorkspace />);
    await screen.findByText("Featuring Robin Tran");
    fireEvent.click(screen.getByRole("button", { name: "Approve new" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
        "This item changed",
    );
    expect(screen.getByText("Featuring Robin Tran")).toBeTruthy();
    expect(
        screen.queryByRole("button", { name: "Undo last decision" }),
    ).toBeNull();
});
it("never renders unsafe source schemes as links", async () => {
    mocks.request.mockImplementation(async (url: string) =>
        url.includes("id=")
            ? {
                  ...item,
                  evidence: [
                      { ...item.evidence[0], url: "javascript:alert(1)" },
                  ],
              }
            : { items: [item], total: 1, page: 1 },
    );
    render(<ReviewWorkspace />);
    await screen.findByText("Featuring Robin Tran");
    expect(screen.queryByRole("link", { name: /Open source/ })).toBeNull();
});
