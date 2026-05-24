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
    it("ignores private-network and localhost seed URLs", async () => {
        const fetchMock = vi.fn();

        const result = await discoverComedianImageCandidates(
            {
                comedianName: "Alex Example",
                website: "http://127.0.0.1:3000/admin",
                websiteScrapingUrl: "http://localhost/press",
            },
            { fetch: fetchMock },
        );

        expect(result).toEqual({
            seedPages: [],
            crawledPages: [],
            candidates: [],
        });
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it.each([
        "http://[::ffff:127.0.0.1]/admin",
        "http://[fc00::1]/admin",
        "http://[fd12:3456:789a::1]/admin",
        "http://[fe80::1]/admin",
        "http://[feb0::1]/admin",
    ])("ignores private IPv6 seed URL %s", async (website) => {
        const fetchMock = vi.fn();

        const result = await discoverComedianImageCandidates(
            {
                comedianName: "Alex Example",
                website,
                websiteScrapingUrl: null,
            },
            { fetch: fetchMock },
        );

        expect(result).toEqual({
            seedPages: [],
            crawledPages: [],
            candidates: [],
        });
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("passes redirect:'error' to page and image fetches", async () => {
        const fetchMock = vi.fn(
            async (input: string | URL | Request, init?: RequestInit) => {
                expect(init?.redirect).toBe("error");
                const url = input.toString();
                if (url === "https://comic.example/") {
                    return htmlResponse(`
                        <img src="/images/headshot.jpg" alt="Alex Example headshot">
                    `);
                }
                if (url === "https://comic.example/images/headshot.jpg") {
                    throw new TypeError("redirect mode set to error");
                }
                throw new Error(`unexpected fetch ${url}`);
            },
        );

        const result = await discoverComedianImageCandidates(
            {
                comedianName: "Alex Example",
                website: "https://comic.example/",
                websiteScrapingUrl: null,
            },
            { fetch: fetchMock },
        );

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(result.candidates).toEqual([]);
    });

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
