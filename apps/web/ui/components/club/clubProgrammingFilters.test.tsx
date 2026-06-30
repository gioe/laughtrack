/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ClubProgrammingFilters from "./clubProgrammingFilters";

const mockReplace = vi.fn();
let currentSearch = "";

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace: mockReplace }),
    useSearchParams: () => new URLSearchParams(currentSearch),
}));

function replacedParams(): URLSearchParams {
    const [href] = mockReplace.mock.calls.at(-1) ?? [""];
    return new URLSearchParams(String(href).replace(/^\?/, ""));
}

beforeEach(() => {
    cleanup();
    mockReplace.mockClear();
    currentSearch = "";
});

describe("ClubProgrammingFilters", () => {
    it("adds a selected programming filter to the club search URL", () => {
        currentSearch = "zip=10001&page=4";

        render(<ClubProgrammingFilters />);
        fireEvent.click(
            screen.getByRole("button", { name: "Improv theaters" }),
        );

        const params = replacedParams();
        expect(params.get("filters")).toBe("improv");
        expect(params.get("zip")).toBe("10001");
        expect(params.get("page")).toBeNull();
    });

    it("preserves existing filters when selecting another programming option", () => {
        currentSearch = "filters=standup&sort=popularityDesc";

        render(<ClubProgrammingFilters />);
        fireEvent.click(
            screen.getByRole("button", { name: "Music venues with comedy" }),
        );

        const params = replacedParams();
        expect(params.get("filters")).toBe("standup,music");
        expect(params.get("sort")).toBe("popularityDesc");
    });

    it("removes a selected programming filter from the club search URL", () => {
        currentSearch = "filters=standup,mixed_programming";

        render(<ClubProgrammingFilters />);
        fireEvent.click(screen.getByRole("button", { name: "Stand-up clubs" }));

        expect(replacedParams().get("filters")).toBe("mixed_programming");
    });
});
