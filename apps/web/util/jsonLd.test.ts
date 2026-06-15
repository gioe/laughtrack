import { describe, it, expect } from "vitest";
import { buildClubJsonLd, buildPodcastJsonLd, buildShowJsonLd } from "./jsonLd";
import { ClubDTO } from "@/objects/class/club/club.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

function baseClub(overrides: Partial<ClubDTO> = {}): ClubDTO {
    return {
        id: 1,
        name: "Test Club",
        imageUrl: "https://cdn.example.com/club.jpg",
        website: "https://testclub.example.com",
        address: "123 Main St, New York, NY 10001",
        city: "New York",
        state: "NY",
        zipCode: "10001",
        ...overrides,
    };
}

describe("buildClubJsonLd", () => {
    it("does not emit description when the field is absent", () => {
        const jsonLd = buildClubJsonLd(baseClub()) as Record<string, unknown>;
        expect(jsonLd.description).toBeUndefined();
    });

    it("emits description when Club.description is non-empty", () => {
        const jsonLd = buildClubJsonLd(
            baseClub({ description: "The best comedy club in town." }),
        ) as Record<string, unknown>;
        expect(jsonLd.description).toBe("The best comedy club in town.");
    });

    it("omits description when Club.description is empty or whitespace", () => {
        const empty = buildClubJsonLd(baseClub({ description: "" })) as Record<
            string,
            unknown
        >;
        expect(empty.description).toBeUndefined();
        const blank = buildClubJsonLd(
            baseClub({ description: "   " }),
        ) as Record<string, unknown>;
        expect(blank.description).toBeUndefined();
    });

    it("strips HTML markup from Club.description", () => {
        // Scraped club descriptions are stored as rich HTML (TASK-2793);
        // structured data must carry plain text.
        const jsonLd = buildClubJsonLd(
            baseClub({
                description:
                    '<p dir="ltr"><strong><span style="color: rgb(0, 0, 0);">Saturday Night Live!</span></strong></p><p dir="ltr">Featuring</p><br>Kate Willett<br>Max Lowe',
            }),
        ) as Record<string, unknown>;
        expect(jsonLd.description).toBe(
            "Saturday Night Live!\n\nFeaturing\n\nKate Willett\nMax Lowe",
        );
    });

    it("omits description when Club.description is markup-only", () => {
        const jsonLd = buildClubJsonLd(
            baseClub({ description: "<p> </p><br>" }),
        ) as Record<string, unknown>;
        expect(jsonLd.description).toBeUndefined();
    });
});

describe("buildShowJsonLd", () => {
    it("marks ticket offers as sold out when show.soldOut is true", () => {
        const show: ShowDTO = {
            id: 1,
            clubId: 2,
            name: "Ronny Chieng: I Love New York City Tour (SOLD OUT)",
            date: new Date("2026-06-20T18:00:00Z"),
            clubName: "Gotham Comedy Club",
            address: "208 W 23rd St",
            imageUrl: "https://cdn.example.com/show.jpg",
            lineup: [],
            tickets: [
                {
                    price: 30,
                    purchaseUrl: "https://tickets.example.com",
                    type: "General Admission",
                    soldOut: false,
                },
            ],
            soldOut: true,
        };

        const jsonLd = buildShowJsonLd(show) as {
            offers: Array<{ availability: string }>;
        };

        expect(jsonLd.offers[0].availability).toBe(
            "https://schema.org/SoldOut",
        );
    });

    it("strips HTML markup from Show.description", () => {
        const show: ShowDTO = {
            id: 1,
            clubId: 2,
            name: "World Cup Watch Party",
            date: new Date("2026-06-20T18:00:00Z"),
            clubName: "Eastville Comedy Club Brooklyn",
            address: "487 Atlantic Ave",
            imageUrl: "https://cdn.example.com/show.jpg",
            lineup: [],
            tickets: [],
            soldOut: false,
            description:
                "<p>Brooklyn's premier viewing lounge.<br><br>What we bring:</p><p>• All you can drink!</p>",
        };

        const jsonLd = buildShowJsonLd(show) as Record<string, unknown>;
        expect(jsonLd.description).toBe(
            "Brooklyn's premier viewing lounge.\n\nWhat we bring:\n\n• All you can drink!",
        );
    });
});

describe("buildPodcastJsonLd", () => {
    function basePodcast(overrides: Partial<PodcastDTO> = {}): PodcastDTO {
        return {
            id: 1,
            slug: "test-pod",
            title: "Test Pod",
            authorName: null,
            websiteUrl: null,
            feedUrl: null,
            imageUrl: null,
            description: null,
            episodeCount: 0,
            hosts: [],
            ...overrides,
        };
    }

    it("strips HTML markup from Podcast.description", () => {
        // 52% of podcast episode descriptions in the DB contain HTML
        // (RSS-sourced); structured data must carry plain text.
        const jsonLd = buildPodcastJsonLd(
            basePodcast({
                description:
                    "<p>Comedy interviews &amp; stories.</p><br>Weekly episodes.",
            }),
            [],
        ) as Record<string, unknown>;
        expect(jsonLd.description).toBe(
            "Comedy interviews & stories.\n\nWeekly episodes.",
        );
    });

    it("omits description when Podcast.description is null or markup-only", () => {
        const nullDesc = buildPodcastJsonLd(basePodcast(), []) as Record<
            string,
            unknown
        >;
        expect(nullDesc.description).toBeUndefined();
        const markupOnly = buildPodcastJsonLd(
            basePodcast({ description: "<p> </p>" }),
            [],
        ) as Record<string, unknown>;
        expect(markupOnly.description).toBeUndefined();
    });
});
