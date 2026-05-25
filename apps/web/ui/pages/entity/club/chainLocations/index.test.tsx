/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
    cleanup,
    fireEvent,
    render,
    screen,
    within,
} from "@testing-library/react";
import ChainLocationDropdown, { ChainLocation } from "./index";

vi.mock("next/link", () => ({
    default: ({
        href,
        children,
        onClick,
        className,
    }: {
        href: string;
        children: React.ReactNode;
        onClick?: () => void;
        className?: string;
    }) => (
        <a href={href} onClick={onClick} className={className}>
            {children}
        </a>
    ),
}));

const locations: ChainLocation[] = [
    {
        name: "New York Comedy Club Midtown",
        locationLabel: "New York, NY",
        isCurrent: true,
    },
    {
        name: "New York Comedy Club East Village",
        locationLabel: "New York, NY",
        isCurrent: false,
    },
    {
        name: "New York Comedy Club Atlanta",
        locationLabel: "Atlanta, GA",
        isCurrent: false,
    },
];

afterEach(() => cleanup());

describe("ChainLocationDropdown", () => {
    it("renders nothing for a single-location chain", () => {
        const { container } = render(
            <ChainLocationDropdown
                chainName="NYCC"
                locations={[locations[0]]}
            />,
        );
        expect(container.firstChild).toBeNull();
    });

    it("shows the current location and toggles the list open", () => {
        render(
            <ChainLocationDropdown
                chainName="New York Comedy Club"
                locations={locations}
            />,
        );

        const toggle = screen.getByRole("button");
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(screen.queryByRole("listbox")).toBeNull();
        expect(
            within(toggle).getByText("New York Comedy Club Midtown"),
        ).toBeTruthy();

        fireEvent.click(toggle);

        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        expect(
            within(screen.getByRole("listbox")).getAllByRole("option"),
        ).toHaveLength(3);
    });

    it("marks the current location and links siblings to their detail page", () => {
        render(
            <ChainLocationDropdown
                chainName="New York Comedy Club"
                locations={locations}
            />,
        );
        fireEvent.click(screen.getByRole("button"));

        const current = screen.getByRole("option", { selected: true });
        expect(current.getAttribute("aria-current")).toBe("true");
        expect(within(current).queryByRole("link")).toBeNull();

        const eastVillage = screen.getByRole("link", { name: /East Village/ });
        expect(eastVillage.getAttribute("href")).toBe(
            "/club/New York Comedy Club East Village",
        );
    });
});
