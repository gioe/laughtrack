/** @vitest-environment happy-dom */
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import CurationWorkspace from "./CurationWorkspace";
import type { InboxDetail } from "@/lib/admin/curation/inboxTypes";
vi.mock("./ReviewWorkspace", () => ({
    default: () => <div>Specialized evidence review</div>,
}));
let item: InboxDetail;
let calls: { url: string; body: any }[];
let submission: "applied" | "pending" | "conflict" | "network";
let submitCount: number;
const response = (body: unknown, status = 200) =>
    Promise.resolve(
        new Response(JSON.stringify(body), {
            status,
            headers: { "Content-Type": "application/json" },
        }),
    );
beforeEach(() => {
    sessionStorage.clear();
    calls = [];
    submission = "applied";
    submitCount = 0;
    item = {
        target: {
            type: "entity",
            id: "podcast-one",
            kind: "podcast",
            scope: "entity",
        },
        label: "A reviewed podcast",
        state: "pending",
        version: 0,
        recordId: 10,
        keys: [
            {
                namespace: "feed-url:v1",
                scope: "global",
                value: "https://example.com/feed",
                key_type: "feed_url",
            },
        ],
        observations: [
            {
                id: "obs",
                source: "RSS",
                source_key: "feed",
                evidence: {
                    title: "Official host evidence",
                    url: "https://example.com",
                },
                recorded_at: "2026-10-01",
            },
        ],
        decisions: [],
        requests: [],
        matches: [],
        reconciliations: [],
        candidateId: null,
    };
    vi.stubGlobal(
        "fetch",
        vi.fn(async (input, init) => {
            const url = String(input),
                body = init?.body ? JSON.parse(String(init.body)) : undefined;
            calls.push({ url, body });
            if (url.includes("/inbox?")) {
                const p = new URL(url, "http://localhost").searchParams;
                return response(
                    p.has("id") ? item : { items: [item], hasMore: false },
                );
            }
            if (url.includes("requestId="))
                return response({ status: "applied" });
            if (body?.operation === "preview")
                return response({
                    available: true,
                    effects: ["Only this identity and its known identifiers."],
                    restoration: "Restore reopens review, without approval.",
                });
            if (body?.operation === "submit") {
                submitCount++;
                if (submission === "network" && submitCount === 1)
                    throw new Error("Connection lost");
                if (submission === "conflict")
                    return response({ error: "This item changed." }, 409);
                if (submission === "pending")
                    return response({ status: "pending" });
                const action = body.command?.action ?? "confirm";
                item = {
                    ...item,
                    state:
                        action === "block"
                            ? "blocked"
                            : action === "restore"
                              ? item.target.type === "entity"
                                  ? "pending"
                                  : "proposed"
                              : action === "sever"
                                ? "severed"
                                : action === "reject"
                                  ? "rejected"
                                  : item.target.type === "entity"
                                    ? "approved"
                                    : "confirmed",
                    version: item.version + 1,
                };
                return response({ status: "applied" });
            }
            throw new Error(url);
        }),
    );
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});
async function ready(filters: Record<string, string> = {}) {
    render(<CurationWorkspace initialFilters={filters} />);
    await screen.findByRole("heading", { name: item.label });
}
async function preview(label: string) {
    fireEvent.change(screen.getByLabelText("Decision reason"), {
        target: { value: "Verified against official source" },
    });
    fireEvent.click(screen.getByRole("button", { name: label }));
    await screen.findByRole("region", { name: "Decision preview" });
}
it("requires a reason and previews a durable block; rediscovery stays blocked, restore only reopens review", async () => {
    await ready();
    expect(
        (
            screen.getByRole("button", {
                name: "Reject and block future intake",
            }) as HTMLButtonElement
        ).disabled,
    ).toBe(true);
    await preview("Reject and block future intake");
    expect(calls.filter((c) => c.body?.operation === "submit")).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByRole("button", { name: "Restore for review" });
    fireEvent.click(screen.getByRole("button", { name: "Refresh queue" }));
    await screen.findByRole("button", { name: "Restore for review" });
    await preview("Restore for review");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByRole("button", { name: "Approve intake" });
    expect(item.state).toBe("pending");
    expect(
        calls
            .filter((c) => c.body?.operation === "submit")
            .map((c) => c.body.command.action),
    ).toEqual(["block", "restore"]);
});
it("retries the exact request after a network interruption", async () => {
    submission = "network";
    await ready();
    await preview("Approve intake");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByText("Connection lost");
    fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
    await screen.findByText(/Decision applied/);
    const attempts = calls.filter((c) => c.body?.operation === "submit");
    expect(attempts).toHaveLength(2);
    expect(attempts[0].body).toEqual(attempts[1].body);
    expect(sessionStorage.getItem("curation-inbox-request-v1")).toBeNull();
});
it("retains a sent request through remount and can check its status", async () => {
    submission = "network";
    await ready();
    await preview("Approve intake");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByText("Connection lost");
    cleanup();
    await ready();
    await screen.findByRole("button", { name: "Check request status" });
    fireEvent.click(
        screen.getByRole("button", { name: "Check request status" }),
    );
    await screen.findByText(/Decision applied/);
    expect(submitCount).toBe(1);
});
it("shows submitted separately from applied and locks a pending decision", async () => {
    submission = "pending";
    await ready();
    await preview("Approve intake");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByText("Submitted, not yet applied.");
    expect(
        (
            screen.getByRole("button", {
                name: "Skip / next",
            }) as HTMLButtonElement
        ).disabled,
    ).toBe(true);
    expect(item.state).toBe("pending");
});
it("requires refreshed state after a conflict", async () => {
    submission = "conflict";
    await ready();
    await preview("Approve intake");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByText("This item changed.");
    expect(
        (
            screen.getByRole("button", {
                name: "Retry same request",
            }) as HTMLButtonElement
        ).disabled,
    ).toBe(true);
    fireEvent.click(
        screen.getByRole("button", { name: "Reload and review again" }),
    );
    await waitFor(() =>
        expect(
            screen.queryByRole("region", { name: "Decision preview" }),
        ).toBeNull(),
    );
    expect(submitCount).toBe(1);
});
it("uses the same panel to establish and sever a host without entity blocking", async () => {
    item = {
        ...item,
        target: { type: "relationship", id: "host-one", kind: "host_of" },
        label: "Alex → Podcast",
        state: "proposed",
        sourceLabel: "Alex",
        targetLabel: "Podcast",
        sourceRecordId: 1,
        targetRecordId: 10,
    };
    await ready({ view: "relationships" });
    expect(
        screen.queryByRole("button", {
            name: "Reject and block future intake",
        }),
    ).toBeNull();
    await preview("Establish relationship");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByRole("button", { name: "Sever relationship" });
    await preview("Sever relationship");
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByRole("button", { name: "Restore for review" });
    expect(item.state).toBe("severed");
});
it("previews parent replacement through the parent service", async () => {
    item = {
        ...item,
        target: { type: "relationship", id: "parent-one", kind: "alias_of" },
        label: "Alias → Canonical",
        state: "proposed",
        sourceRecordId: 1,
        targetRecordId: 2,
    };
    await ready({ view: "relationships" });
    await preview("Establish relationship");
    const call = calls.find((c) => c.url === "/api/admin/curation/parents");
    expect(call?.body).toMatchObject({
        operation: "preview",
        childId: 1,
        parentId: 2,
    });
});
it("supports direct links and skips by keyboard without deciding; typing J does not skip", async () => {
    await ready({ id: "podcast-one", state: "blocked", q: "reviewed" });
    expect(calls.some((c) => c.url.includes("id=podcast-one"))).toBe(true);
    fireEvent.keyDown(screen.getByLabelText("Decision reason"), { key: "j" });
    expect(screen.getByRole("heading", { name: item.label })).toBeTruthy();
    fireEvent.keyDown(window, { key: "j" });
    await screen.findByRole("heading", { name: "Select a review" });
    expect(submitCount).toBe(0);
    fireEvent.click(
        await screen.findByRole("button", { name: "Review queue (1)" }),
    );
    expect(
        screen
            .getByRole("button", { name: "Review queue (1)" })
            .getAttribute("aria-expanded"),
    ).toBe("true");
});
it.each(["comedian", "club", "show", "podcast"] as const)(
    "supports scoped %s intake",
    async (kind) => {
        item = {
            ...item,
            target: {
                type: "entity",
                id: "one",
                kind,
                scope: kind === "show" ? "series" : "entity",
            },
            candidateId: kind === "comedian" ? "candidate" : null,
        };
        await ready();
        expect(
            screen.getByRole("button", {
                name: "Reject and block future intake",
            }),
        ).toBeTruthy();
        if (kind === "show")
            expect(
                screen.getByText(
                    "Source-owned recurring series, including future occurrences",
                ),
            ).toBeTruthy();
        if (kind === "comedian")
            expect(
                screen
                    .getByRole("link", {
                        name: "Validate performer evidence and choose appearances",
                    })
                    .getAttribute("href"),
            ).toContain("candidate");
    },
);

it.each(["alias_of", "host_of"])(
    "stages %s evidence before establishing a pair",
    async (role) => {
        const original = global.fetch;
        const endpoints = [
            {
                ...item,
                target: {
                    type: "entity",
                    kind: "comedian",
                    id: "comic",
                    scope: "entity",
                },
                label: "Alex Example",
                recordId: 1,
                state: "approved",
            },
            {
                ...item,
                target: {
                    type: "entity",
                    kind: role === "alias_of" ? "comedian" : "podcast",
                    id: "destination",
                    scope: "entity",
                },
                label: "Destination",
                recordId: 2,
                state: "approved",
            },
        ];
        vi.stubGlobal(
            "fetch",
            vi.fn(async (input, init) => {
                const url = String(input),
                    body = init?.body
                        ? JSON.parse(String(init.body))
                        : undefined;
                if (url.includes("lookup=")) {
                    const query = new URL(
                        url,
                        "http://localhost",
                    ).searchParams.get("q");
                    return response({
                        items: [query === "Alex" ? endpoints[0] : endpoints[1]],
                    });
                }
                if (body?.operation === "propose") {
                    calls.push({ url, body });
                    item = {
                        ...item,
                        target: {
                            type: "relationship",
                            id: "new-pair",
                            kind: role as "alias_of" | "host_of",
                        },
                        label: "Alex Example → Destination",
                        state: "proposed",
                        sourceRecordId: 1,
                        targetRecordId: 2,
                    };
                    return response({ relationshipId: "new-pair" });
                }
                return original(input, init);
            }),
        );
        await ready({ view: "relationships" });
        fireEvent.click(
            screen.getByRole("button", { name: "Propose relationship" }),
        );
        fireEvent.change(screen.getByLabelText("Relationship role"), {
            target: { value: role },
        });
        fireEvent.change(
            screen.getByLabelText(
                role === "alias_of" ? "Child comedian" : "Comedian",
                { exact: true },
            ),
            { target: { value: "Alex" } },
        );
        fireEvent.click(
            await screen.findByRole("button", { name: /Alex Example · ID 1/ }),
        );
        fireEvent.change(
            screen.getByLabelText(
                role === "alias_of" ? "Canonical parent" : "Podcast",
                { exact: true },
            ),
            { target: { value: "Destination" } },
        );
        fireEvent.click(
            await screen.findByRole("button", { name: /Destination · ID 2/ }),
        );
        fireEvent.change(screen.getByLabelText("Evidence URL"), {
            target: { value: "https://example.org/credits" },
        });
        fireEvent.change(
            screen.getByLabelText(
                role === "alias_of"
                    ? "Why both names identify the same performer"
                    : "Evidence of this hosting role",
            ),
            {
                target: {
                    value: "Official credits identify the performer and role explicitly.",
                },
            },
        );
        fireEvent.change(screen.getByLabelText("Proposal reason"), {
            target: { value: "Verified official credits" },
        });
        fireEvent.click(
            screen.getByRole("button", {
                name: "Save evidence and review pair",
            }),
        );
        await screen.findByRole("heading", {
            name: "Alex Example → Destination",
        });
        expect(item.state).toBe("proposed");
        expect(
            calls.filter((c) => c.body?.operation === "submit"),
        ).toHaveLength(0);
        expect(calls.find((c) => c.body?.operation === "propose")?.url).toBe(
            `/api/admin/curation/${role === "alias_of" ? "parents" : "hosts"}`,
        );
    },
);
it("requires an explicit canonical reconciliation preview and retries its immutable token", async () => {
    item = {
        ...item,
        target: { type: "relationship", id: "host", kind: "host_of" },
        state: "confirmed",
        reconciliations: [
            { id: "hold", resolved_at: null, actor: null, reason: null },
        ],
    };
    const original = global.fetch;
    vi.stubGlobal(
        "fetch",
        vi.fn(async (input, init) => {
            const body = init?.body ? JSON.parse(String(init.body)) : undefined;
            if (body?.operation === "previewReconciliation") {
                calls.push({ url: String(input), body });
                return response({
                    token: "exact-state-token",
                    effects: [
                        "Retain confirmed old decision and rejected new decision.",
                    ],
                });
            }
            if (body?.operation === "reconcile") {
                calls.push({ url: String(input), body });
                return response({ status: "applied" });
            }
            return original(input, init);
        }),
    );
    await ready({ view: "relationships" });
    fireEvent.change(screen.getByLabelText("Decision reason"), {
        target: { value: "Retain both reviewed decisions" },
    });
    fireEvent.click(
        screen.getByRole("button", { name: "Preview reconciliation" }),
    );
    await screen.findByText(
        "Retain confirmed old decision and rejected new decision.",
    );
    expect(calls.filter((c) => c.body?.operation === "reconcile")).toHaveLength(
        0,
    );
    fireEvent.click(screen.getByRole("button", { name: "Apply decision" }));
    await screen.findByText(/Decision applied/);
    expect(
        calls.find((c) => c.body?.operation === "reconcile")?.body.input,
    ).toMatchObject({
        id: "hold",
        token: "exact-state-token",
        reason: "Retain both reviewed decisions",
    });
    expect(item.state).toBe("confirmed");
});
