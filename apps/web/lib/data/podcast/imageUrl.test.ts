import { describe, expect, it } from "vitest";
import { buildPodcastArtworkUrl, safePodcastImageUrl } from "./imageUrl";

describe("podcast image URLs", () => {
    it("keeps only HTTPS upstream artwork URLs", () => {
        expect(safePodcastImageUrl("https://cdn.example.com/art.jpg")).toBe(
            "https://cdn.example.com/art.jpg",
        );
        expect(safePodcastImageUrl("http://cdn.example.com/art.jpg")).toBeNull();
        expect(safePodcastImageUrl(null)).toBeNull();
    });

    it("builds same-origin proxy URLs for Next image optimization", () => {
        expect(
            buildPodcastArtworkUrl(
                "https://cdn.example.com/artwork/funny show.jpg",
            ),
        ).toBe(
            "/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fartwork%2Ffunny%20show.jpg",
        );
    });
});
