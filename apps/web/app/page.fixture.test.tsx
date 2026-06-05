import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { CAROUSEL_TEST_IDS } from "@/lib/data/home/homeFixtures";

vi.mock("@/ui/pages/home/shows", () => ({
    default: ({
        title,
        testId,
        seeAllHref,
        shows,
    }: {
        title: string;
        testId: string;
        seeAllHref: string;
        shows: unknown[];
    }) => (
        <section
            data-testid={testId}
            data-href={seeAllHref}
            data-count={shows.length}
        >
            {title}
        </section>
    ),
}));

import FixtureHomePage from "./page.fixture";

describe("FixtureHomePage", () => {
    it("renders a deterministic Nearby Shows carousel for manual home verification", () => {
        const markup = renderToStaticMarkup(<FixtureHomePage />);

        expect(markup).toContain("Nearby Shows");
        expect(markup).toContain(
            `data-testid="${CAROUSEL_TEST_IDS.nearbyShows}"`,
        );
        expect(markup).toContain('data-count="3"');
        expect(markup).toContain(
            'data-href="/show/search?zip=10801&amp;distance=25"',
        );
    });
});
