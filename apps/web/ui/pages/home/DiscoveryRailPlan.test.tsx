/**
 * @vitest-environment happy-dom
 */

import type { ReactNode } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import DiscoveryRailPlan, {
    type DiscoveryRailPayloads,
    type DiscoveryRailPlanData,
} from "./DiscoveryRailPlan";

const mocks = vi.hoisted(() => ({
    renderedShows: [] as ShowDTO[],
}));

vi.mock("@/ui/components/cards/show", () => ({
    default: ({
        show,
        discoveryAttribution,
    }: {
        show: ShowDTO;
        discoveryAttribution?: { onShowDetail: () => void };
    }) => {
        mocks.renderedShows.push(show);
        return (
            <button
                type="button"
                data-testid={`show-${show.id}`}
                data-sold-out={String(show.soldOut === true)}
                onClick={discoveryAttribution?.onShowDetail}
            >
                {show.name}
                {show.soldOut ? " · Sold Out" : ""}
            </button>
        );
    },
}));

vi.mock("./shows/DiscoveryImpressionTracker", () => ({
    default: ({
        surface,
        policyVersion,
        experimentVariant,
        rank,
        children,
        className,
    }: {
        surface: string;
        policyVersion: string;
        experimentVariant: string;
        rank: number;
        children: (attribution: {
            impressionId: string;
            onShowDetail: () => void;
        }) => ReactNode;
        className?: string;
    }) => (
        <div
            className={className}
            data-testid={`tracker-${surface}-${rank}`}
            data-surface={surface}
            data-policy-version={policyVersion}
            data-experiment-variant={experimentVariant}
            data-rank={rank}
        >
            {children({
                impressionId: `impression-${surface}-${rank}`,
                onShowDetail: vi.fn(),
            })}
        </div>
    ),
}));

vi.mock("./comedians", () => ({
    default: ({ comedians }: { comedians: Array<{ name: string }> }) => (
        <div data-testid="comedian-rail">
            {comedians.map((comedian) => comedian.name).join("|")}
        </div>
    ),
}));

vi.mock("./clubs", () => ({
    default: ({
        clubs,
        preserveOrder,
    }: {
        clubs: Array<{ name: string }>;
        preserveOrder?: boolean;
    }) => (
        <div
            data-testid="club-rail"
            data-preserve-order={String(preserveOrder)}
        >
            {clubs.map((club) => club.name).join("|")}
        </div>
    ),
}));

function show(id: number, soldOut = false): ShowDTO {
    return {
        id,
        clubId: 1,
        clubName: "Comedy Club",
        date: new Date("2026-08-08T20:00:00.000Z"),
        tickets: soldOut
            ? [
                  {
                      soldOut: true,
                      purchaseUrl: "https://tickets.example.com",
                      price: 25,
                      type: "general admission",
                  },
              ]
            : [],
        name: `Show ${id}`,
        imageUrl: "/show.jpg",
        soldOut,
    };
}

function payloads(): DiscoveryRailPayloads {
    return {
        followedComedianShows: [show(21), show(22)],
        trendingComedians: [
            { id: 101, name: "Comic 101" },
            { id: 102, name: "Comic 102" },
        ] as unknown as DiscoveryRailPayloads["trendingComedians"],
        showsTonight: [show(11), show(12)],
        moreNearYou: [show(31), show(32)],
        trendingThisWeek: [show(41), show(42)],
        popularClubs: [
            { id: 1, name: "Club One", activeComedianCount: 1 },
            { id: 2, name: "Club Two", activeComedianCount: 20 },
        ] as unknown as DiscoveryRailPayloads["popularClubs"],
        dynamicRails: [],
    };
}

function plan(rails: DiscoveryRailPlanData["rails"]): DiscoveryRailPlanData {
    return {
        version: 1,
        catalogVersion: 3,
        policyVersion: 9,
        platform: "web",
        cycleIndex: 100,
        rails,
    };
}

function renderPlan(
    railPlan: DiscoveryRailPlanData | null | undefined,
    nextPayloads = payloads(),
) {
    return render(
        <DiscoveryRailPlan
            plan={railPlan}
            payloads={nextPayloads}
            fallback={<div data-testid="legacy-fallback">Legacy rails</div>}
            today="2026-08-08"
            weekEnd="2026-08-14"
            zipCode="10001"
            distanceMiles={25}
            localTrendingComedians
            localPopularClubs
        />,
    );
}

beforeEach(() => {
    mocks.renderedShows.length = 0;
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("DiscoveryRailPlan", () => {
    it("renders supported rails and itemIds in server order", () => {
        renderPlan(
            plan([
                {
                    railKey: "popular_clubs",
                    payloadKey: "popularClubs",
                    position: 0,
                    itemIds: ["2", "1"],
                },
                {
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 1,
                    itemIds: ["12", "11"],
                },
                {
                    railKey: "trending_comedians",
                    payloadKey: "trendingComedians",
                    position: 2,
                    itemIds: ["102", "101"],
                },
            ]),
        );

        const rails = Array.from(
            document.querySelectorAll("[data-discovery-rail-key]"),
        );
        expect(
            rails.map((rail) => rail.getAttribute("data-discovery-rail-key")),
        ).toEqual(["popular_clubs", "shows_tonight", "trending_comedians"]);
        expect(screen.getByTestId("club-rail").textContent).toBe(
            "Club Two|Club One",
        );
        expect(
            screen.getByTestId("club-rail").getAttribute("data-preserve-order"),
        ).toBe("true");
        expect(
            mocks.renderedShows
                .map((item) => item.id)
                .filter((id, index, ids) => ids.indexOf(id) === index),
        ).toEqual([12, 11]);
        expect(screen.getByTestId("comedian-rail").textContent).toBe(
            "Comic 102|Comic 101",
        );
    });

    it("uses fallback and unknown rails safely", () => {
        const { rerender } = renderPlan(null);
        expect(screen.getByTestId("legacy-fallback")).toBeTruthy();

        rerender(
            <DiscoveryRailPlan
                plan={plan([])}
                payloads={payloads()}
                fallback={<div data-testid="legacy-fallback">Legacy rails</div>}
                today="2026-08-08"
                weekEnd="2026-08-14"
            />,
        );
        expect(screen.getByTestId("legacy-fallback")).toBeTruthy();

        rerender(
            <DiscoveryRailPlan
                plan={plan([
                    {
                        railKey: "future_ai_comedy",
                        payloadKey: "futurePayload",
                        position: 0,
                        itemIds: ["1"],
                    },
                    {
                        railKey: "shows_tonight",
                        payloadKey: "wrongPayload",
                        position: 1,
                        itemIds: ["11"],
                    },
                ])}
                payloads={payloads()}
                fallback={<div data-testid="legacy-fallback">Legacy rails</div>}
                today="2026-08-08"
                weekEnd="2026-08-14"
            />,
        );
        expect(screen.getByTestId("legacy-fallback")).toBeTruthy();

        rerender(
            <DiscoveryRailPlan
                plan={plan([
                    {
                        railKey: "future_ai_comedy",
                        payloadKey: "futurePayload",
                        position: 0,
                        itemIds: ["1"],
                    },
                    {
                        railKey: "shows_tonight",
                        payloadKey: "showsTonight",
                        position: 1,
                        itemIds: ["11"],
                    },
                ])}
                payloads={payloads()}
                fallback={<div data-testid="legacy-fallback">Legacy rails</div>}
                today="2026-08-08"
                weekEnd="2026-08-14"
            />,
        );
        expect(screen.queryByTestId("legacy-fallback")).toBeNull();
        expect(
            document.querySelector(
                '[data-discovery-rail-key="future_ai_comedy"]',
            ),
        ).toBeNull();
        expect(screen.getByTestId("show-11")).toBeTruthy();
    });

    it("uses show-card presentation without reason copy or See all and preserves sold-out DTOs", () => {
        const soldOut = show(71, true);
        const omitted = show(72);
        const nextPayloads = payloads();
        nextPayloads.dynamicRails = [
            {
                railKey: "starting_to_buzz",
                label: "Shows gaining momentum",
                items: [
                    {
                        id: 71,
                        show: soldOut,
                        reason: {
                            kind: "starting_to_buzz",
                            label: "Ticket interest is climbing quickly",
                            evidence: { confidence: 0.9 },
                        },
                    },
                    {
                        id: 72,
                        show: omitted,
                        reason: {
                            kind: "starting_to_buzz",
                            label: "This unselected item must stay hidden",
                        },
                    },
                ],
            },
        ];

        renderPlan(
            plan([
                {
                    railKey: "starting_to_buzz",
                    payloadKey: "dynamicRails",
                    position: 0,
                    itemIds: ["71"],
                },
            ]),
            nextPayloads,
        );

        expect(
            screen.queryByText("Ticket interest is climbing quickly"),
        ).toBeNull();
        expect(
            screen.queryByText("This unselected item must stay hidden"),
        ).toBeNull();
        expect(screen.getByTestId("show-71").textContent).toContain("Sold Out");
        expect(
            screen.getByTestId("show-71").getAttribute("data-sold-out"),
        ).toBe("true");
        expect(mocks.renderedShows[0]).toBe(soldOut);
        expect(screen.queryByText("See all →")).toBeNull();
    });

    it("limits Rarely nearby to eight shows", () => {
        const items = Array.from({ length: 10 }, (_, index) => ({
            id: index + 1,
            show: show(index + 1),
            reason: {
                kind: "just_passing_through",
                label: `Comic ${index + 1} is visiting`,
            },
        }));
        const nextPayloads = payloads();
        nextPayloads.dynamicRails = [
            {
                railKey: "just_passing_through",
                label: "Rarely nearby",
                items,
            },
        ];

        renderPlan(
            plan([
                {
                    railKey: "just_passing_through",
                    payloadKey: "dynamicRails",
                    position: 0,
                    itemIds: items.map(({ id }) => String(id)),
                },
            ]),
            nextPayloads,
        );

        expect(
            mocks.renderedShows
                .map(({ id }) => id)
                .filter((id, index, ids) => ids.indexOf(id) === index),
        ).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    });

    it("limits Tonight and followed-comedian rails to eight shows", () => {
        const tonight = Array.from({ length: 10 }, (_, index) =>
            show(index + 1),
        );
        const followed = Array.from({ length: 10 }, (_, index) =>
            show(index + 11),
        );
        const nextPayloads = payloads();
        nextPayloads.showsTonight = tonight;
        nextPayloads.followedComedianShows = followed;

        renderPlan(
            plan([
                {
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 0,
                    itemIds: tonight.map(({ id }) => String(id)),
                },
                {
                    railKey: "followed_comedian_shows",
                    payloadKey: "followedComedianShows",
                    position: 1,
                    itemIds: followed.map(({ id }) => String(id)),
                },
            ]),
            nextPayloads,
        );

        expect(
            mocks.renderedShows
                .map(({ id }) => id)
                .filter((id, index, ids) => ids.indexOf(id) === index),
        ).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18]);
    });

    it("passes rail key, policy version, and rank for analytics attribution", () => {
        renderPlan(
            plan([
                {
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 0,
                    itemIds: ["12", "11"],
                },
            ]),
        );

        const first = screen.getByTestId("tracker-shows_tonight-1");
        const second = screen.getByTestId("tracker-shows_tonight-2");
        expect(first.getAttribute("data-surface")).toBe("shows_tonight");
        expect(first.getAttribute("data-policy-version")).toBe("9");
        expect(first.getAttribute("data-experiment-variant")).toBe(
            "server_directed",
        );
        expect(first.getAttribute("data-rank")).toBe("1");
        expect(second.getAttribute("data-rank")).toBe("2");
    });
});
