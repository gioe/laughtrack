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
import AdminCreateButton from "./AdminCreateButton";

const mocks = vi.hoisted(() => ({
    pathname: "/admin/comedians",
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    usePathname: () => mocks.pathname,
    useRouter: () => ({ refresh: mocks.refresh }),
}));

afterEach(() => {
    cleanup();
});

beforeEach(() => {
    vi.clearAllMocks();
    mocks.pathname = "/admin/comedians";
    vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ ok: true }),
        }),
    );
});

describe("AdminCreateButton", () => {
    it("opens the comedian creation modal from the floating plus button", async () => {
        render(<AdminCreateButton />);

        fireEvent.click(screen.getByRole("button", { name: "Create item" }));

        expect(
            screen.getByRole("dialog", { name: "Create comedian" }),
        ).toBeTruthy();
        fireEvent.change(screen.getByLabelText("Name"), {
            target: { value: "New Comic" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Create comedian" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({ name: "New Comic" }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("opens the club creation modal with required club fields", async () => {
        mocks.pathname = "/admin/clubs";
        render(<AdminCreateButton />);

        fireEvent.click(screen.getByRole("button", { name: "Create item" }));

        expect(
            screen.getByRole("dialog", { name: "Create club" }),
        ).toBeTruthy();
        expect(screen.getByLabelText("Name").hasAttribute("required")).toBe(
            true,
        );
        expect(screen.getByLabelText("Address").hasAttribute("required")).toBe(
            true,
        );
        expect(screen.getByLabelText("Website").hasAttribute("required")).toBe(
            true,
        );

        fireEvent.change(screen.getByLabelText("Name"), {
            target: { value: "New Club" },
        });
        fireEvent.change(screen.getByLabelText("Address"), {
            target: { value: "123 Main St" },
        });
        fireEvent.change(screen.getByLabelText("Website"), {
            target: { value: "https://newclub.example.com" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Create club" }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/clubs",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        name: "New Club",
                        address: "123 Main St",
                        website: "https://newclub.example.com",
                    }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });
});
