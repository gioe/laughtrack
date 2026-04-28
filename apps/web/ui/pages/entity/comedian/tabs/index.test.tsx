/**
 * @vitest-environment happy-dom
 */
import React, { useEffect } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";
import ComedianDetailTabs from "./index";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";

let pastMountCount = 0;

vi.mock("@/ui/pages/search/table", () => ({
    default: () => <div data-testid="upcoming-shows">Upcoming shows</div>,
}));

vi.mock("@/ui/pages/search/filterBar", () => ({
    default: () => <div data-testid="filter-bar">Filters</div>,
}));

vi.mock("@/ui/pages/entity/comedian/pastShows", () => ({
    default: function MockPastShowsSection() {
        useEffect(() => {
            pastMountCount += 1;
        }, []);

        return <div data-testid="past-shows">Past show markup</div>;
    },
}));

vi.mock("@/ui/pages/entity/comedian/related", () => ({
    default: () => <div data-testid="related-comedians">Related comedians</div>,
}));

const renderTabs = () =>
    render(
        <ComedianDetailTabs
            shows={[{ id: 1 } as ShowDTO]}
            total={1}
            filters={[]}
            comedianName="Jane Comic"
            relatedComedians={[{ id: 2 } as ComedianDTO]}
        />,
    );

describe("ComedianDetailTabs", () => {
    beforeEach(() => {
        pastMountCount = 0;
    });

    afterEach(() => {
        cleanup();
    });

    it("renders only upcoming show markup on first paint", () => {
        const { container } = renderTabs();

        expect(
            container.querySelector('[data-testid="upcoming-shows"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="filter-bar"]'),
        ).not.toBeNull();
        expect(
            container.querySelector('[data-testid="past-shows"]'),
        ).toBeNull();
        expect(
            container.querySelector('[data-testid="related-comedians"]'),
        ).toBeNull();
    });

    it("keeps the past tab mounted after first activation", () => {
        const { getByRole, container } = renderTabs();

        fireEvent.click(getByRole("tab", { name: /past/i }));
        expect(
            container.querySelector('[data-testid="past-shows"]'),
        ).not.toBeNull();
        expect(pastMountCount).toBe(1);

        fireEvent.click(getByRole("tab", { name: /related/i }));
        fireEvent.click(getByRole("tab", { name: /past/i }));

        expect(pastMountCount).toBe(1);
    });
});
