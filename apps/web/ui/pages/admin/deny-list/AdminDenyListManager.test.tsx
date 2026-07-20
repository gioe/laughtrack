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
import AdminDenyListManager, {
    type AdminDenyListEntry,
} from "./AdminDenyListManager";

const mocks = vi.hoisted(() => ({
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        refresh: mocks.refresh,
    }),
}));

const entry: AdminDenyListEntry = {
    name: "Jimmy Dore",
    reason: "Not a comedian",
    addedBy: "admin@example.com",
    addedAt: "2026-07-19T12:00:00.000Z",
};

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

describe("AdminDenyListManager", () => {
    it("adds an entry and refreshes after success", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockResolvedValueOnce({ ok: true } as Response);
        render(<AdminDenyListManager entries={[]} />);

        fireEvent.change(screen.getByLabelText("Name"), {
            target: { value: "New Name" },
        });
        fireEvent.change(screen.getByLabelText("Reason"), {
            target: { value: "Confirmed non-comedian" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Add" }));

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith("/api/admin/deny-list", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: "New Name",
                    reason: "Confirmed non-comedian",
                }),
            });
        });
        expect(await screen.findByText("Entry saved.")).toBeTruthy();
        await waitFor(() => {
            expect(
                (screen.getByLabelText("Name") as HTMLInputElement).value,
            ).toBe("");
            expect(
                (screen.getByLabelText("Reason") as HTMLInputElement).value,
            ).toBe("");
            expect(mocks.refresh).toHaveBeenCalledOnce();
        });
    });

    it("removes an entry with a reason and refreshes after success", async () => {
        const fetchMock = vi.mocked(fetch);
        fetchMock.mockResolvedValueOnce({ ok: true } as Response);
        render(<AdminDenyListManager entries={[entry]} />);

        fireEvent.change(screen.getByLabelText("Removal reason"), {
            target: { value: "  Added by mistake  " },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Remove Jimmy Dore" }),
        );

        await waitFor(() => {
            expect(fetchMock).toHaveBeenCalledWith("/api/admin/deny-list", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: "Jimmy Dore",
                    reason: "Added by mistake",
                }),
            });
        });
        expect(await screen.findByText("Entry removed.")).toBeTruthy();
        await waitFor(() => {
            expect(
                (screen.getByLabelText("Removal reason") as HTMLInputElement)
                    .value,
            ).toBe("");
            expect(mocks.refresh).toHaveBeenCalledOnce();
        });
    });

    it("requires a non-whitespace removal reason", () => {
        render(<AdminDenyListManager entries={[entry]} />);
        const removeButton = screen.getByRole("button", {
            name: "Remove Jimmy Dore",
        }) as HTMLButtonElement;
        const reasonInput = screen.getByLabelText("Removal reason");

        expect(removeButton.disabled).toBe(true);
        fireEvent.change(reasonInput, { target: { value: "   " } });
        expect(removeButton.disabled).toBe(true);
        fireEvent.change(reasonInput, { target: { value: "Duplicate entry" } });
        expect(removeButton.disabled).toBe(false);
    });

    it("renders an API error without clearing add inputs", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
            ok: false,
            status: 409,
            json: async () => ({ error: "Entry already exists" }),
        } as Response);
        render(<AdminDenyListManager entries={[]} />);

        fireEvent.change(screen.getByLabelText("Name"), {
            target: { value: "Existing Name" },
        });
        fireEvent.change(screen.getByLabelText("Reason"), {
            target: { value: "Needs review" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Add" }));

        expect(await screen.findByText("Entry already exists")).toBeTruthy();
        expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe(
            "Existing Name",
        );
        expect(
            (screen.getByLabelText("Reason") as HTMLInputElement).value,
        ).toBe("Needs review");
        expect(mocks.refresh).not.toHaveBeenCalled();
    });

    it("renders a network error without clearing the removal reason", async () => {
        vi.mocked(fetch).mockRejectedValueOnce(new Error("Connection lost"));
        render(<AdminDenyListManager entries={[entry]} />);

        fireEvent.change(screen.getByLabelText("Removal reason"), {
            target: { value: "Retain this explanation" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Remove Jimmy Dore" }),
        );

        expect(await screen.findByText("Connection lost")).toBeTruthy();
        expect(
            (screen.getByLabelText("Removal reason") as HTMLInputElement).value,
        ).toBe("Retain this explanation");
        expect(mocks.refresh).not.toHaveBeenCalled();
    });
});
