import { describe, expect, it } from "vitest";
import { buildPodcastArtworkUrl, safePodcastImageUrl } from "./imageUrl";

describe("podcast image URLs", () => {
    it("keeps secure upstream artwork URLs", () => {
        expect(safePodcastImageUrl("https://cdn.example.com/art.jpg")).toBe(
            "https://cdn.example.com/art.jpg",
        );
        expect(safePodcastImageUrl(null)).toBeNull();
    });

    it("upgrades RSS artwork URLs to HTTPS", () => {
        expect(safePodcastImageUrl("http://cdn.example.com/art.jpg")).toBe(
            "https://cdn.example.com/art.jpg",
        );
        expect(
            safePodcastImageUrl("//cdn.example.com/art.jpg"),
        ).toBe("https://cdn.example.com/art.jpg");
    });

    it("rejects invalid and non-web artwork URLs", () => {
        expect(safePodcastImageUrl("")).toBeNull();
        expect(safePodcastImageUrl("not a url")).toBeNull();
        expect(
            safePodcastImageUrl("ftp://cdn.example.com/art.jpg"),
        ).toBeNull();
    });

    it("builds same-origin proxy URLs for Next image optimization", () => {
        expect(
            buildPodcastArtworkUrl(
                "http://cdn.example.com/artwork/funny show.jpg",
            ),
        ).toBe(
            "/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fartwork%2Ffunny%20show.jpg",
        );
    });
});
