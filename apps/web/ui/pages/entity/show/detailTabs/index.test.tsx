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
    it("wraps lineup + related shows in the tab strip when isOpenMic is false and both are non-empty", () => {
        render(
            <ShowDetailTabs
                lineup={lineup}
                relatedShows={relatedShows}
                clubName="Copper Room"
            />,
        );

        // The tab strip wrapper is the meaningful branch signal — without
        // it, a regression that drops the strip would still find both child
        // testids and pass spuriously.
        expect(screen.getByTestId("detail-tabs")).not.toBeNull();
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

    it("renders nothing visible when isOpenMic is true and relatedShows is empty", () => {
        render(
            <ShowDetailTabs
                lineup={lineup}
                relatedShows={[]}
                clubName="Copper Room"
                isOpenMic
            />,
        );

        expect(screen.queryByTestId("lineup-section")).toBeNull();
        // RelatedShowsSection is mocked to a stub div; the real component
        // returns null for empty shows, but the mock always renders. The
        // intent here is that lineup stays suppressed and no tab strip wraps
        // the lone related-shows slot.
        expect(screen.queryByTestId("detail-tabs")).toBeNull();
    });
});
