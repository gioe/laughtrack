import { describe, expect, it, vi } from "vitest";

import { discoverComedianImageCandidates } from "./comedianImageDiscovery";

function htmlResponse(html: string) {
    return new Response(html, {
        status: 200,
        headers: { "content-type": "text/html; charset=utf-8" },
    });
}

function imageResponse(contentType = "image/jpeg") {
    return new Response(new Uint8Array([1, 2, 3]), {
        status: 200,
        headers: { "content-type": contentType },
    });
}

describe("discoverComedianImageCandidates", () => {
    it("only crawls official-site seed pages and same-origin discovery links", async () => {
        const fetchMock = vi.fn(async (input: string | URL | Request) => {
            const url = input.toString();
            if (url === "https://comic.example/") {
                return htmlResponse(`
                    <a href="/press">Press</a>
                    <a href="https://social.example/comic">Social</a>
                    <img src="/images/headshot.jpg" alt="Alex Example headshot">
                    <img src="https://cdn.example/not-official.jpg" alt="external">
                `);
            }
            if (url === "https://comic.example/press") {
                return htmlResponse(`
                    <img src="/images/press-photo.jpg" alt="Alex Example press photo">
                `);
            }
            if (
                url === "https://comic.example/images/headshot.jpg" ||
                url === "https://comic.example/images/press-photo.jpg"
            ) {
                return imageResponse();
            }
            throw new Error(`unexpected fetch ${url}`);
        });

        const result = await discoverComedianImageCandidates(
            {
                comedianName: "Alex Example",
                website: "https://comic.example/",
                websiteScrapingUrl: null,
            },
            {
                fetch: fetchMock,
                inspectImage: vi.fn(async (url) => ({
                    url,
                    width: url.includes("headshot") ? 1200 : 900,
                    height: url.includes("headshot") ? 1600 : 1200,
                    mimeType: "image/jpeg",
                })),
            },
        );

        expect(result.seedPages).toEqual(["https://comic.example/"]);
        expect(fetchMock).not.toHaveBeenCalledWith(
            "https://social.example/comic",
            expect.anything(),
        );
        expect(
            result.candidates.map((candidate) => candidate.imageUrl),
        ).toEqual([
            "https://comic.example/images/headshot.jpg",
            "https://comic.example/images/press-photo.jpg",
        ]);
        expect(
            result.candidates.every((candidate) =>
                candidate.sourcePage.startsWith("https://comic.example/"),
            ),
        ).toBe(true);
    });

    it("ranks headshot and press images above poster and logo images", async () => {
        const fetchMock = vi.fn(async (input: string | URL | Request) => {
            const url = input.toString();
            if (url === "https://comic.example/") {
                return htmlResponse(`
                    <img src="/assets/show-poster.jpg" alt="Alex Example tour poster">
                    <img src="/assets/logo.png" alt="Alex Example logo">
                    <img src="/assets/headshot.jpg" alt="Alex Example headshot">
                    <img src="/assets/press-photo.jpg" alt="Alex Example press photo">
                `);
            }
            return imageResponse(
                url.endsWith(".png") ? "image/png" : "image/jpeg",
            );
        });

        const result = await discoverComedianImageCandidates(
            {
                comedianName: "Alex Example",
                website: "https://comic.example/",
                websiteScrapingUrl: null,
            },
            {
                fetch: fetchMock,
                inspectImage: vi.fn(async (url) => ({
                    url,
                    width: url.includes("logo") ? 240 : 1200,
                    height: url.includes("logo") ? 120 : 1600,
                    mimeType: url.endsWith(".png") ? "image/png" : "image/jpeg",
                })),
            },
        );

        expect(
            result.candidates.map((candidate) => candidate.imageUrl),
        ).toEqual([
            "https://comic.example/assets/headshot.jpg",
            "https://comic.example/assets/press-photo.jpg",
            "https://comic.example/assets/show-poster.jpg",
            "https://comic.example/assets/logo.png",
        ]);
        expect(result.candidates[0].reasons).toContain("headshot signal");
        expect(result.candidates[1].reasons).toContain("press signal");
        expect(result.candidates[3].reasons).toContain("logo penalty");
    });
});
