/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Calendar, MapPin } from "lucide-react";
import EmptyState from "@/ui/components/emptyState";

afterEach(() => {
    cleanup();
});

describe("EmptyState tones", () => {
    it("renders the empty tone with iOS-style default copy and sparkles icon", () => {
        const { container } = render(<EmptyState />);

        expect(
            screen.getByRole("heading", { level: 2, name: "No matches yet" }),
        ).toBeTruthy();
        expect(
            screen.getByText(
                "Try broadening your search or removing a filter.",
            ),
        ).toBeTruthy();
        expect(container.querySelectorAll("svg")).toHaveLength(1);
    });

    it("renders the error tone as an alert with actionable copy and custom action", () => {
        render(
            <EmptyState
                tone="error"
                action={<button type="button">Try again</button>}
            />,
        );

        expect(screen.getByRole("alert")).toBeTruthy();
        expect(
            screen.getByRole("heading", {
                level: 2,
                name: "Couldn't refresh results",
            }),
        ).toBeTruthy();
        expect(
            screen.getByText(
                "The latest update did not finish. Try again in a moment.",
            ),
        ).toBeTruthy();
        expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
    });

    it("keeps explicit title, message, and icon overrides for existing callers", () => {
        const { container } = render(
            <EmptyState
                title="No saved clubs"
                message="Save a club to track its upcoming shows."
                icons={[Calendar, MapPin]}
            />,
        );

        expect(
            screen.getByRole("heading", { level: 2, name: "No saved clubs" }),
        ).toBeTruthy();
        expect(
            screen.getByText("Save a club to track its upcoming shows."),
        ).toBeTruthy();
        expect(container.querySelectorAll("svg")).toHaveLength(2);
    });

    it("renders loading state as busy and suppresses actions", () => {
        render(
            <EmptyState
                tone="loading"
                action={<button type="button">Browse all shows</button>}
            />,
        );

        const state = screen
            .getByRole("heading", {
                level: 2,
                name: "Fetching nearby shows",
            })
            .closest("[aria-busy='true']");

        expect(state).toBeTruthy();
        expect(
            screen.getByText(
                "We're checking clubs, comedians, and upcoming dates.",
            ),
        ).toBeTruthy();
        expect(
            screen.queryByRole("button", { name: "Browse all shows" }),
        ).toBeNull();
    });
});
