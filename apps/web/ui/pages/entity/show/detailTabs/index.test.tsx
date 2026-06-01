/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowDetailTabs from "./index";
import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";

vi.mock("@/ui/pages/entity/show/lineupSection", () => ({
    default: () => <div data-testid="lineup-section" />,
}));

vi.mock("@/ui/pages/entity/show/relatedShows", () => ({
    default: () => <div data-testid="related-shows" />,
}));

vi.mock("@/ui/pages/entity/detailTabs", () => ({
    default: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="detail-tabs">{children}</div>
    ),
    DetailTab: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const lineup: ComedianLineupDTO[] = [
    { id: 1, name: "Sample Comedian" } as unknown as ComedianLineupDTO,
];
const relatedShows: ShowDTO[] = [
    { id: 99 } as unknown as ShowDTO,
];

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("ShowDetailTabs", () => {
    it("renders the lineup section when isOpenMic is false and lineup is non-empty", () => {
        render(
            <ShowDetailTabs
                lineup={lineup}
                relatedShows={relatedShows}
                clubName="Copper Room"
            />,
        );

        expect(screen.getByTestId("lineup-section")).not.toBeNull();
        expect(screen.getByTestId("related-shows")).not.toBeNull();
    });

    it("suppresses the lineup section when isOpenMic is true, even with a non-empty lineup", () => {
        render(
            <ShowDetailTabs
                lineup={lineup}
                relatedShows={relatedShows}
                clubName="Copper Room"
                isOpenMic
            />,
        );

        expect(screen.queryByTestId("lineup-section")).toBeNull();
        expect(screen.getByTestId("related-shows")).not.toBeNull();
        // No tab strip when only related shows remain.
        expect(screen.queryByTestId("detail-tabs")).toBeNull();
    });
});
