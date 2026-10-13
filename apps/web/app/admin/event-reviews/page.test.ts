import { expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));
import Page from "./page";
it("redirects legacy event review bookmarks into the shared inbox", async () => {
    await Page({
        searchParams: Promise.resolve({
            source: "2",
            mode: "shadow",
            q: "Friday",
            id: "7",
            after: "50",
            ceiling: "80",
        }),
    });
    const url = new URL(mocks.redirect.mock.calls[0][0], "http://localhost");
    expect(url.pathname).toBe("/admin/reviews");
    expect(Object.fromEntries(url.searchParams)).toEqual({
        workflow: "event_eligibility",
        status: "all",
        source: "2",
        mode: "shadow",
        q: "Friday",
        id: "7",
        after: "50",
        ceiling: "80",
    });
});
