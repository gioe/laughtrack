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
    fireEvent.change(screen.getByLabelText(/Decision note/), {
        target: { value: "Verified performer evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link existing" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
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
    fireEvent.change(screen.getByLabelText(/Decision note/), {
        target: { value: "Verified performer evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve new" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
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

const eventItem = {
    ...item,
    id: "1",
    workflow: "event_eligibility",
    status: "review",
    matches: [],
    actions: ["approve", "reject", "defer"],
    notice: "Shadow mode · automated flags alone do not withhold events.",
    title: "Comedy Night",
    subtitle: "Harvelles · November 1",
    evidence: [
        {
            ...item.evidence[0],
            showId: undefined,
            context: "Explicit stand-up billing",
        },
    ],
};
function mockEvent(overrides = {}) {
    mocks.request.mockImplementation(
        async (url: string, init?: RequestInit) => {
            if (init?.method === "POST")
                return {
                    status: "pending",
                    notice: "Review submitted; awaiting worker validation.",
                };
            if (url.includes("id=")) return { ...eventItem, ...overrides };
            return {
                items: [{ ...eventItem, ...overrides }],
                total: null,
                page: 1,
                cursor: { ceiling: 51, next: 50 },
            };
        },
    );
}
it.each(["Approve event", "Reject", "Defer"])(
    "requires a reason and confirmation for %s, reports queued rather than applied",
    async (label) => {
        mockEvent();
        render(
            <ReviewWorkspace
                initialFilters={{ workflow: "event_eligibility" }}
            />,
        );
        await screen.findByText("Explicit stand-up billing");
        expect(
            (screen.getByRole("button", { name: label }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
        fireEvent.change(screen.getByLabelText(/Decision note/), {
            target: { value: "Explicit venue comedy billing" },
        });
        fireEvent.click(screen.getByRole("button", { name: label }));
        expect(
            mocks.request.mock.calls.some(([, i]) => i?.method === "POST"),
        ).toBe(false);
        fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
        await screen.findByText(
            "Review submitted; awaiting worker validation.",
        );
        const call = mocks.request.mock.calls.find(
            ([, i]) => i?.method === "POST",
        )!;
        expect(JSON.parse(call[1].body)).toMatchObject({
            workflow: "event_eligibility",
            id: "1",
            token: "token",
            reason: "Explicit venue comedy billing",
            action: label === "Approve event" ? "approve" : label.toLowerCase(),
            requestId: expect.any(String),
        });
        expect(
            screen.queryByRole("button", { name: "Undo last decision" }),
        ).toBeNull();
    },
);
it("reuses the event request ID after a lost response", async () => {
    mockEvent();
    const implementation = mocks.request.getMockImplementation()!;
    let posts = 0;
    mocks.request.mockImplementation(async (url, init) => {
        if (init?.method === "POST" && ++posts === 1)
            throw Error("Connection lost");
        return implementation(url, init);
    });
    render(
        <ReviewWorkspace initialFilters={{ workflow: "event_eligibility" }} />,
    );
    await screen.findByText("Explicit stand-up billing");
    fireEvent.change(screen.getByLabelText(/Decision note/), {
        target: { value: "Explicit comedy" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Defer" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await screen.findByText("Connection lost");
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await screen.findByText("Review submitted; awaiting worker validation.");
    const bodies = mocks.request.mock.calls
        .filter(([, i]) => i?.method === "POST")
        .map(([, i]) => JSON.parse(i.body));
    expect(bodies).toHaveLength(2);
    expect(bodies[1]).toEqual(bodies[0]);
});
it("uses stable event cursors and honors a selected legacy deep link", async () => {
    mockEvent();
    render(
        <ReviewWorkspace
            initialFilters={{
                workflow: "event_eligibility",
                id: "99",
                source: "2",
                mode: "shadow",
            }}
        />,
    );
    await screen.findByText("Explicit stand-up billing");
    await waitFor(() =>
        expect(
            mocks.request.mock.calls.some(
                ([u]) => u.includes("source=2") && u.includes("mode=shadow"),
            ),
        ).toBe(true),
    );
    expect(mocks.request.mock.calls.some(([u]) => u.includes("id=99"))).toBe(
        true,
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() =>
        expect(
            mocks.request.mock.calls.some(
                ([u]) => u.includes("after=50") && u.includes("ceiling=51"),
            ),
        ).toBe(true),
    );
});
it("shows read-only event evidence without decision controls", async () => {
    mockEvent({
        actions: [],
        processing: true,
        notice: "Review submitted; awaiting worker validation.",
    });
    render(
        <ReviewWorkspace initialFilters={{ workflow: "event_eligibility" }} />,
    );
    await screen.findByText("Explicit stand-up billing");
    expect(screen.queryByRole("button", { name: "Approve event" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Defer" })).toBeNull();
});
it("uses the same evidence and action panel for podcast relationships", async () => {
    mocks.request.mockImplementation(async (url, init) =>
        init?.method === "POST"
            ? { decisionId: "decision" }
            : url.includes("id=")
              ? { ...item, workflow: "podcast_association", matches: [] }
              : { items: [item], total: 1, page: 1 },
    );
    render(
        <ReviewWorkspace
            initialFilters={{ workflow: "podcast_association" }}
        />,
    );
    await screen.findByText("Featuring Robin Tran");
    fireEvent.click(
        screen.getByRole("button", { name: "Approve relationship" }),
    );
    await screen.findByRole("button", { name: "Undo last decision" });
});

it.each(["comedian_visibility", "club_visibility"])(
    "reviews %s blocking with reason, confirmation, and attributed history",
    async (workflow) => {
        const review = {
            ...item,
            id: "9",
            workflow,
            status: "active",
            actions: ["block"],
            matches: [],
            history: [
                {
                    id: "h",
                    action: "Previous review",
                    reason: "Earlier decision",
                    actor: "admin",
                    createdAt: "2026-10-12T00:00:00Z",
                    undone: false,
                },
            ],
        };
        mocks.request.mockImplementation(async (url, init) =>
            init?.method === "POST"
                ? { notice: "Robin Tran: blocked." }
                : url.includes("id=")
                  ? review
                  : { items: [review], total: 1, page: 1 },
        );
        render(<ReviewWorkspace initialFilters={{ workflow, id: "9" }} />);
        await screen.findByText("Featuring Robin Tran");
        expect(
            (
                screen.getByRole("button", {
                    name: "Hide publicly",
                }) as HTMLButtonElement
            ).disabled,
        ).toBe(true);
        fireEvent.change(screen.getByLabelText(/Decision note/), {
            target: { value: "Duplicate public record" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Hide publicly" }));
        expect(
            mocks.request.mock.calls.some(([, i]) => i?.method === "POST"),
        ).toBe(false);
        expect(
            screen.getByText(/changes public visibility immediately/),
        ).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
        await screen.findByText("Robin Tran: blocked.");
        const post = mocks.request.mock.calls.find(
            ([, i]) => i?.method === "POST",
        )!;
        expect(JSON.parse(post[1].body)).toEqual({
            workflow,
            id: "9",
            token: "token",
            action: "block",
            reason: "Duplicate public record",
        });
        expect(
            screen.queryByRole("button", { name: "Undo last decision" }),
        ).toBeNull();
    },
);
it("offers unblock for a blocked record and preserves evidence on conflict", async () => {
    const review = {
        ...item,
        workflow: "club_visibility",
        status: "blocked",
        actions: ["unblock"],
        matches: [],
    };
    mocks.request.mockImplementation(async (url, init) => {
        if (init?.method === "POST")
            throw Error("This item changed. Refresh it before deciding.");
        return url.includes("id=")
            ? review
            : { items: [review], total: 1, page: 1 };
    });
    render(
        <ReviewWorkspace
            initialFilters={{ workflow: "club_visibility", status: "blocked" }}
        />,
    );
    await screen.findByText("Featuring Robin Tran");
    expect(screen.queryByRole("button", { name: "Hide publicly" })).toBeNull();
    fireEvent.change(screen.getByLabelText(/Decision note/), {
        target: { value: "Validated venue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Show publicly" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await screen.findByText("This item changed. Refresh it before deciding.");
    expect(screen.getByText("Featuring Robin Tran")).toBeTruthy();
});
it("keeps multiple performers selected across searches and previews joint resolution", async () => {
    const joint = {
        ...item,
        title: "Josh Martier & Ben Staab",
        matches: [{ id: 10, name: "Josh Martier" }],
    };
    mocks.request.mockImplementation(
        async (url: string, init?: RequestInit) => {
            if (init?.method === "POST")
                return { decisionId: "joint-decision" };
            if (url.includes("search=")) return [{ id: 11, name: "Ben Staab" }];
            if (url.includes("id=")) return joint;
            return { items: [joint], total: 1, page: 1 };
        },
    );
    render(<ReviewWorkspace />);
    fireEvent.click(
        await screen.findByRole("button", {
            name: "Add Josh Martier to billing",
        }),
    );
    fireEvent.change(screen.getByLabelText("Match an existing comedian"), {
        target: { value: "Ben" },
    });
    fireEvent.click(
        await screen.findByRole("button", { name: "Add Ben Staab to billing" }),
    );
    fireEvent.change(screen.getByLabelText("Source billing observation"), {
        target: { value: "e" },
    });
    fireEvent.click(screen.getByLabelText("Also confirm this show appearance"));
    fireEvent.change(screen.getByLabelText(/Decision note/), {
        target: { value: "Verified both co-headliners" },
    });
    fireEvent.click(
        screen.getByRole("button", { name: "Resolve to multiple performers" }),
    );
    expect(
        screen.getByText(/Josh Martier \+ Ben Staab for source/),
    ).toBeTruthy();
    expect(
        mocks.request.mock.calls.some(([, init]) => init?.method === "POST"),
    ).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Confirm review" }));
    await waitFor(() =>
        expect(
            mocks.request.mock.calls.some(
                ([, init]) => init?.method === "POST",
            ),
        ).toBe(true),
    );
    const call = mocks.request.mock.calls.find(
        ([, init]) => init?.method === "POST",
    )!;
    expect(JSON.parse(call[1].body)).toMatchObject({
        action: "resolve_multiple",
        targetIds: [10, 11],
        evidenceId: "e",
        showIds: [1],
    });
});
