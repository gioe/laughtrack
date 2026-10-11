/** @vitest-environment happy-dom */
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import EventReviews, { screeningEffect, sourceUrl } from "./EventReviews";
import type { EventReviewRow } from "@/lib/admin/eventReviews";
const row = {
    candidate_id: 1,
    club_id: 10,
    source_id: 2,
    club_name: "Harvelles",
    scraper_key: "seatengine",
    gate_mode: "shadow",
    source_policy: "mixed",
    enabled: true,
    policy_version: 1,
    current_policy_version: 1,
    decision_id: 3,
    review_version: 0,
    status: "review",
    decision: "review",
    token: "a".repeat(64),
    payload: {
        name: "Comedy Night",
        description: "Explicit stand-up billing",
        date: "2026-11-01T20:00:00Z",
        url: "javascript:alert(1)",
    },
    evidence: {
        performers: [
            {
                names: ["Alias"],
                canonical_id: 8,
                state: "unblocked",
                diagnostics: ["canonical_parent_resolved"],
            },
        ],
        reason_codes: ["missing_lineup"],
    },
} as unknown as EventReviewRow;
const fetcher = vi.fn();
beforeEach(() => {
    vi.stubGlobal("fetch", fetcher);
    fetcher.mockReset();
    fetcher.mockImplementation(async (url: string, options?: RequestInit) => {
        if (options?.method === "POST")
            return Response.json({ status: "pending" }, { status: 202 });
        if (url.includes("?id="))
            return Response.json({
                current: row,
                history: [],
                observations: [],
                publications: [],
                requests: [],
            });
        return Response.json({ items: [row], ceiling: 1, next: null });
    });
});
afterEach(cleanup);
async function select() {
    render(<EventReviews />);
    fireEvent.click(
        await screen.findByRole("button", { name: /review shadow mode/ }),
    );
    await screen.findByText("Explicit stand-up billing");
}
it("shows evidence, parent resolution and shadow behavior; requires confirmation before submission", async () => {
    await select();
    expect(screen.getByText(/Resolved comedian ID: 8/)).toBeTruthy();
    expect(
        screen.getByText(/automated flags alone do not withhold/),
    ).toBeTruthy();
    expect(
        screen.queryByRole("link", { name: "Open source event" }),
    ).toBeNull();
    fireEvent.change(screen.getByLabelText("Reason"), {
        target: { value: "Comedy is explicitly billed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview decision" }));
    expect(
        fetcher.mock.calls.filter(([, o]) => o?.method === "POST"),
    ).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await screen.findByText(/Review submitted/);
    const call = fetcher.mock.calls.find(([, o]) => o?.method === "POST")!;
    expect(JSON.parse(call[1].body)).toMatchObject({
        candidateId: 1,
        token: row.token,
        action: "approve",
        reason: "Comedy is explicitly billed",
    });
    expect(JSON.parse(call[1].body).actor).toBeUndefined();
});
it("keeps the same request ID on a retry after a lost response", async () => {
    await select();
    fireEvent.change(screen.getByLabelText("Reason"), {
        target: { value: "Verified" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview decision" }));
    fetcher.mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === "POST") throw new Error("Network interrupted");
        throw new Error("unexpected");
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await waitFor(() =>
        expect(
            fetcher.mock.calls.filter(([, o]) => o?.method === "POST"),
        ).toHaveLength(2),
    );
    const bodies = fetcher.mock.calls
        .filter(([, o]) => o?.method === "POST")
        .map(([, o]) => JSON.parse(o.body));
    expect(bodies[0].id).toBe(bodies[1].id);
});
it("keeps off observations read-only and explains pending state", async () => {
    fetcher.mockImplementation(async (url: string) =>
        Response.json(
            url.includes("?id=")
                ? {
                      current: { ...row, gate_mode: "off" },
                      history: [],
                      observations: [],
                      publications: [],
                      requests: [],
                  }
                : { items: [row], ceiling: 1, next: null },
        ),
    );
    await select();
    expect(screen.getByText(/Screening off/)).toBeTruthy();
    expect(
        screen.queryByRole("button", { name: "Preview decision" }),
    ).toBeNull();
});
it("describes human holds in shadow and refuses executable source URLs", () => {
    expect(
        screeningEffect({ ...row, status: "reject", review_version: 1 }),
    ).toMatch(/Human hold/);
    expect(sourceUrl("data:text/html,bad")).toBeNull();
    expect(sourceUrl("https://example.com/event")).toBe(
        "https://example.com/event",
    );
});
