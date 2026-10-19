import { expect, it, vi } from "vitest";
const redirect = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ redirect }));
import Page from "./page";
it("routes podcast decision controls into Review Inbox", () => {
    Page();
    expect(redirect).toHaveBeenCalledWith(
        "/admin/reviews?view=relationships&kind=host_of",
    );
});
