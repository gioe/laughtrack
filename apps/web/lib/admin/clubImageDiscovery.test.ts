import { describe, expect, it, vi } from "vitest";

import { discoverClubImageCandidates } from "./clubImageDiscovery";

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

describe("discoverClubImageCandidates", () => {
    it("ignores private-network and localhost seed URLs", async () => {
        const fetchMock = vi.fn();

        const result = await discoverClubImageCandidates(
            {
                clubName: "Comedy Club",
                website: "http://127.0.0.1:3000/admin",
                websiteScrapingUrl: "http://localhost/photos",
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

        const result = await discoverClubImageCandidates(
            {
                clubName: "Comedy Club",
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
                if (url === "https://club.example/") {
                    return htmlResponse(`
                        <img src="/assets/logo.png" alt="Comedy Club logo">
                    `);
                }
                if (url === "https://club.example/assets/logo.png") {
                    throw new TypeError("redirect mode set to error");
                }
                throw new Error(`unexpected fetch ${url}`);
            },
        );

        const result = await discoverClubImageCandidates(
            {
                clubName: "Comedy Club",
                website: "https://club.example/",
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
            if (url === "https://club.example/") {
                return htmlResponse(`
                    <a href="/about">About</a>
                    <a href="https://social.example/club">Social</a>
                    <img src="/images/logo.png" alt="Giggle Lounge logo">
                    <img src="https://cdn.example/not-official.png" alt="external logo">
                `);
            }
            if (url === "https://club.example/about") {
                return htmlResponse(`
                    <img src="/images/venue.jpg" alt="venue interior banner">
                `);
            }
            if (
                url === "https://club.example/images/logo.png" ||
                url === "https://club.example/images/venue.jpg"
            ) {
                return imageResponse();
            }
            throw new Error(`unexpected fetch ${url}`);
        });

        const result = await discoverClubImageCandidates(
            {
                clubName: "Giggle Lounge",
                website: "https://club.example/",
                websiteScrapingUrl: null,
            },
            {
                fetch: fetchMock,
                inspectImage: vi.fn(async (url) => ({
                    url,
                    width: url.includes("logo") ? 500 : 1200,
                    height: url.includes("logo") ? 500 : 800,
                    mimeType: "image/jpeg",
                })),
            },
        );

        expect(result.seedPages).toEqual(["https://club.example/"]);
        expect(fetchMock).not.toHaveBeenCalledWith(
            "https://social.example/club",
            expect.anything(),
        );
        expect(
            result.candidates.map((candidate) => candidate.imageUrl),
        ).toEqual([
            "https://club.example/images/logo.png",
            "https://club.example/images/venue.jpg",
        ]);
        expect(
            result.candidates.every((candidate) =>
                candidate.sourcePage.startsWith("https://club.example/"),
            ),
        ).toBe(true);
    });

    it("ranks logo, og:image, and venue banner above headshot and poster", async () => {
        const fetchMock = vi.fn(async (input: string | URL | Request) => {
            const url = input.toString();
            if (url === "https://club.example/") {
                return htmlResponse(`
                    <meta property="og:image" content="https://club.example/social/preview.jpg">
                    <img src="/assets/logo.png" alt="Laffs Comedy logo wordmark">
                    <img src="/photos/interior.jpg" alt="Club interior banner photo">
                    <img src="/people/headshot.jpg" alt="Comedian headshot portrait">
                    <img src="/events/tour-poster.jpg" alt="Spring tour lineup poster">
                `);
            }
            return imageResponse(
                url.endsWith(".png") ? "image/png" : "image/jpeg",
            );
        });

        const dimsFor = (url: string): [number, number] => {
            if (url.includes("logo")) return [600, 240];
            if (url.includes("preview")) return [1200, 630];
            if (url.includes("interior")) return [1600, 900];
            if (url.includes("poster")) return [1080, 1920];
            return [800, 1000]; // headshot
        };

        const result = await discoverClubImageCandidates(
            {
                clubName: "Laffs Comedy",
                website: "https://club.example/",
                websiteScrapingUrl: null,
            },
            {
                fetch: fetchMock,
                inspectImage: vi.fn(async (url) => {
                    const [width, height] = dimsFor(url);
                    return {
                        url,
                        width,
                        height,
                        mimeType: url.endsWith(".png")
                            ? "image/png"
                            : "image/jpeg",
                    };
                }),
            },
        );

        expect(
            result.candidates.map((candidate) => candidate.imageUrl),
        ).toEqual([
            "https://club.example/assets/logo.png",
            "https://club.example/social/preview.jpg",
            "https://club.example/photos/interior.jpg",
            "https://club.example/events/tour-poster.jpg",
            "https://club.example/people/headshot.jpg",
        ]);
        expect(result.candidates[0].reasons).toContain("logo / wordmark signal");
        expect(result.candidates[1].reasons).toContain(
            "og:image / social preview",
        );
        expect(result.candidates[2].reasons).toContain("venue / banner signal");
        expect(result.candidates[4].reasons).toContain(
            "portrait / person penalty",
        );
    });
});
