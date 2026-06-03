import { describe, expect, it, vi } from "vitest";

vi.hoisted(() => {
    process.env.BUNNYCDN_CDN_HOST = "cdn.example.com";
});

import {
    buildComedianImageAssetUrl,
    buildComedianImageUrls,
} from "./imageAssets";

describe("comedian image asset URLs", () => {
    it("uses active stable avatar and hero asset paths when present", () => {
        const urls = buildComedianImageUrls({
            name: "Taylor Tomlinson",
            hasImage: true,
            activeAsset: {
                avatarPath: "/comedians/42/avatar.webp",
                heroPath: "/comedians/42/hero.webp",
            },
        });

        expect(urls.avatarUrl).toBe(
            "https://cdn.example.com/comedians/42/avatar.webp",
        );
        expect(urls.heroUrl).toBe(
            "https://cdn.example.com/comedians/42/hero.webp",
        );
        expect(urls.imageUrl).toBe(
            "https://cdn.example.com/comedians/42/avatar.webp",
        );
    });

    it("falls back to the name-based PNG when no active asset exists", () => {
        const urls = buildComedianImageUrls({
            name: "Taylor Tomlinson",
            hasImage: true,
            activeAsset: null,
        });

        expect(urls.avatarUrl).toBe(
            "https://cdn.example.com/comedians/Taylor%20Tomlinson.png",
        );
        expect(urls.heroUrl).toBe(
            "https://cdn.example.com/comedians/Taylor%20Tomlinson.png",
        );
        expect(urls.imageUrl).toBe(
            "https://cdn.example.com/comedians/Taylor%20Tomlinson.png",
        );
    });

    it("preserves hasImage=false as an empty URL when no active asset exists", () => {
        const urls = buildComedianImageUrls({
            name: "Taylor Tomlinson",
            hasImage: false,
            activeAsset: null,
        });

        expect(urls).toEqual({
            avatarUrl: "",
            heroUrl: "",
            imageUrl: "",
        });
    });

    it("falls back per variant when an active asset is only partially populated", () => {
        const urls = buildComedianImageUrls({
            name: "Taylor Tomlinson",
            hasImage: true,
            activeAsset: {
                avatarPath: "/comedians/42/avatar.webp",
                heroPath: null,
            },
        });

        expect(urls.avatarUrl).toBe(
            "https://cdn.example.com/comedians/42/avatar.webp",
        );
        expect(urls.heroUrl).toBe(
            "https://cdn.example.com/comedians/Taylor%20Tomlinson.png",
        );
        expect(urls.imageUrl).toBe(
            "https://cdn.example.com/comedians/42/avatar.webp",
        );
    });

    it("builds CDN URLs for stored paths with or without a leading slash", () => {
        expect(buildComedianImageAssetUrl("comedians/42/hero.webp")).toBe(
            "https://cdn.example.com/comedians/42/hero.webp",
        );
        expect(buildComedianImageAssetUrl("/comedians/42/hero.webp")).toBe(
            "https://cdn.example.com/comedians/42/hero.webp",
        );
    });

    it("rejects absolute asset paths that would escape the CDN host", () => {
        expect(() =>
            buildComedianImageAssetUrl("https://images.example.com/hero.webp"),
        ).toThrow("Comedian image asset path must be CDN-relative");
        expect(() =>
            buildComedianImageAssetUrl("//images.example.com/hero.webp"),
        ).toThrow("Comedian image asset path must be CDN-relative");
    });
});
