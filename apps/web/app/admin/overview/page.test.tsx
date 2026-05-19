import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    redirect: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    redirect: mocks.redirect,
}));

import AdminOverviewPage from "./page";

describe("AdminOverviewPage", () => {
    it("redirects the old overview route to users", () => {
        AdminOverviewPage();

        expect(mocks.redirect).toHaveBeenCalledWith("/admin/users");
    });
});
