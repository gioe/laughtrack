/**
 * @vitest-environment happy-dom
 */

import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AdminClubEditor from "./AdminClubEditor";

const mocks = vi.hoisted(() => ({
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        refresh: mocks.refresh,
    }),
}));

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

function renderEditor() {
    render(
        <AdminClubEditor
            clubId={42}
            clubName="Comedy Cellar"
            initialDescription="Original description"
        />,
    );
}

describe("AdminClubEditor", () => {
    it("PATCHes a description, shows success, and refreshes the route", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockImplementation(
            async () =>
                new Response(JSON.stringify({ ok: true }), { status: 200 }),
        );
        renderEditor();

        fireEvent.change(screen.getByLabelText("Description"), {
            target: { value: "  Updated description  " },
        });
        fireEvent.click(screen.getByRole("button", { name: "Save" }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith("/api/admin/clubs/42", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    description: "  Updated description  ",
                }),
            });
        });
        expect(await screen.findByText("Saved.")).toBeTruthy();
        await waitFor(() => expect(mocks.refresh).toHaveBeenCalledTimes(1));
    });

    it("normalizes a whitespace-only description to null", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockImplementation(
            async () =>
                new Response(JSON.stringify({ ok: true }), { status: 200 }),
        );
        renderEditor();

        fireEvent.change(screen.getByLabelText("Description"), {
            target: { value: "   \n" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Save" }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/admin/clubs/42",
                expect.objectContaining({
                    body: JSON.stringify({ description: null }),
                }),
            );
        });
    });

    it("shows an API error without refreshing the route", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockImplementation(
            async () =>
                new Response(
                    JSON.stringify({ error: "Description is invalid" }),
                    { status: 422 },
                ),
        );
        renderEditor();

        fireEvent.click(screen.getByRole("button", { name: "Save" }));

        expect(await screen.findByText("Description is invalid")).toBeTruthy();
        expect(mocks.refresh).not.toHaveBeenCalled();
    });

    it("shows a network error without refreshing the route", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockRejectedValueOnce(new Error("Network unavailable"));
        renderEditor();

        fireEvent.click(screen.getByRole("button", { name: "Save" }));

        expect(await screen.findByText("Network unavailable")).toBeTruthy();
        expect(mocks.refresh).not.toHaveBeenCalled();
    });
});
