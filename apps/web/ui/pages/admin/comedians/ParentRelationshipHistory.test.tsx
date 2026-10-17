/** @vitest-environment happy-dom */
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ParentRelationshipHistory } from "./ParentRelationshipHistory";
const edge = {
    id: "edge",
    child_name: "Stage Name",
    parent_name: "Real Name",
    disposition: "rejected",
    version: 1,
    decisions: [
        {
            id: "d",
            action: "reject",
            actor: "admin",
            reason: "Not the same performer",
        },
    ],
    observations: [
        {
            id: "o",
            evidence: {
                sourceUrl: "https://example.org",
                explanation: "Reviewed biography",
            },
        },
    ],
};
beforeEach(() => {
    vi.stubGlobal(
        "fetch",
        vi
            .fn()
            .mockResolvedValue({
                ok: true,
                json: async () => ({ relationships: [edge] }),
            }),
    );
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});
it("shows evidence and negative history, previews restore and requires a separate apply", async () => {
    render(
        <ParentRelationshipHistory
            childId={1}
            reason="New evidence found"
            refreshKey={0}
        />,
    );
    await screen.findByText("Stage Name → Real Name: rejected");
    fireEvent.click(screen.getByText("Relationship history (1)"));
    expect(
        screen.getByText("reject: Not the same performer — admin"),
    ).toBeTruthy();
    expect(
        screen.getByRole("link", { name: "Evidence" }).getAttribute("href"),
    ).toBe("https://example.org");
    vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ effects: ["Reopen for review only"] }),
    } as never);
    fireEvent.click(screen.getByRole("button", { name: "Restore for review" }));
    await screen.findByText("Reopen for review only");
    expect(
        JSON.parse(vi.mocked(fetch).mock.calls[1][1]!.body as string),
    ).toMatchObject({
        operation: "preview",
        command: { action: "restore", expectedVersion: 1 },
    });
    vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "applied" }),
    } as never);
    fireEvent.click(
        screen.getByRole("button", { name: "Apply history decision" }),
    );
    await waitFor(() => expect(vi.mocked(fetch).mock.calls).toHaveLength(4));
    expect(
        JSON.parse(vi.mocked(fetch).mock.calls[2][1]!.body as string).operation,
    ).toBe("submit");
});
it("requires a reason and reports stale decisions without hiding history", async () => {
    const { rerender } = render(
        <ParentRelationshipHistory childId={1} reason="" refreshKey={0} />,
    );
    await screen.findByText("Stage Name → Real Name: rejected");
    fireEvent.click(screen.getByText("Relationship history (1)"));
    fireEvent.click(screen.getByRole("button", { name: "Restore for review" }));
    expect(screen.getByRole("alert").textContent).toContain(
        "Enter a relationship reason",
    );
    expect(fetch).toHaveBeenCalledTimes(1);
    rerender(
        <ParentRelationshipHistory
            childId={1}
            reason="Review again"
            refreshKey={0}
        />,
    );
    vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ error: "Refresh the stale decision" }),
    } as never);
    fireEvent.click(screen.getByRole("button", { name: "Restore for review" }));
    await screen.findByText("Refresh the stale decision");
    expect(screen.getByText("Stage Name → Real Name: rejected")).toBeTruthy();
});
