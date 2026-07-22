import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveInstagramFollowerCount } from "./instagramFollowerResolver";

const followerResponse = (count: number) => ({
    status: 200,
    body: { data: { user: { edge_followed_by: { count } } } },
});

describe("resolveInstagramFollowerCount", () => {
    afterEach(() => {
        vi.unstubAllEnvs();
    });

    it("falls back for Taylor's deleted Instagram schema response", async () => {
        vi.stubEnv("INSTAGRAM_FETCH_ATTEMPTS", "1");
        const fetchProfile = vi.fn().mockResolvedValue({
            status: 400,
            body: {
                message:
                    "Asset asset://laser.provider/ig_business_category_subvertical has been deleted. You cannot use this schema",
            },
        });
        const fetchProfileHtml = vi.fn().mockResolvedValue({
            status: 200,
            body: '<meta property="og:description" content="3M Followers, 1,481 Following, 2,031 Posts">',
        });
        const warn = vi.fn();

        await expect(
            resolveInstagramFollowerCount("taylortomlinson", {
                fetchProfile,
                fetchProfileHtml,
                warn,
            }),
        ).resolves.toEqual({
            status: "resolved",
            followerCount: 3_000_000,
        });

        expect(fetchProfileHtml).toHaveBeenCalledWith(
            expect.objectContaining({
                href: "https://www.instagram.com/taylortomlinson/?hl=en",
            }),
            expect.objectContaining({ Accept: "text/html" }),
        );
        expect(JSON.parse(warn.mock.calls[0][0])).toEqual(
            expect.objectContaining({
                event: "instagram_follower_resolution_fallback",
                primaryFailure: "http_error",
            }),
        );
    });

    it.each([
        ["27K", 27_000],
        ["3M", 3_000_000],
        ["20m", 20_000_000],
        ["1.2B", 1_200_000_000],
        ["123,456", 123_456],
    ])("parses the HTML follower label %s", async (label, expected) => {
        vi.stubEnv("INSTAGRAM_FETCH_ATTEMPTS", "1");
        const fetchProfileHtml = vi.fn().mockResolvedValue({
            status: 200,
            body: `<meta content="${label} Followers, 10 Following" name="description">`,
        });

        await expect(
            resolveInstagramFollowerCount("formattedcomic", {
                fetchProfile: vi
                    .fn()
                    .mockResolvedValue({ status: 401, body: null }),
                fetchProfileHtml,
                warn: vi.fn(),
            }),
        ).resolves.toEqual({ status: "resolved", followerCount: expected });
    });

    it("does not fallback for a confirmed missing account", async () => {
        const fetchProfileHtml = vi.fn();

        await expect(
            resolveInstagramFollowerCount("missingcomic", {
                fetchProfile: vi
                    .fn()
                    .mockResolvedValue({ status: 404, body: null }),
                fetchProfileHtml,
                sleep: vi.fn().mockResolvedValue(undefined),
            }),
        ).resolves.toEqual({ status: "not_found" });

        expect(fetchProfileHtml).not.toHaveBeenCalled();
    });

    it("retains failure when the HTML fallback is malformed", async () => {
        vi.stubEnv("INSTAGRAM_FETCH_ATTEMPTS", "1");

        await expect(
            resolveInstagramFollowerCount("blockedcomic", {
                fetchProfile: vi
                    .fn()
                    .mockResolvedValue({ status: 400, body: null }),
                fetchProfileHtml: vi.fn().mockResolvedValue({
                    status: 200,
                    body: '<meta property="og:description" content="Profile unavailable">',
                }),
                warn: vi.fn(),
            }),
        ).resolves.toEqual({
            status: "failed",
            detail: "Instagram returned status 400",
        });
    });

    it("uses the Instagram web profile endpoint and reads the follower count", async () => {
        const fetchProfile = vi
            .fn()
            .mockResolvedValue(followerResponse(123_456));

        await expect(
            resolveInstagramFollowerCount("@aliascomic", { fetchProfile }),
        ).resolves.toEqual({ status: "resolved", followerCount: 123_456 });

        expect(fetchProfile).toHaveBeenCalledTimes(1);
        expect(fetchProfile).toHaveBeenCalledWith(
            expect.objectContaining({
                href: "https://i.instagram.com/api/v1/users/web_profile_info/?username=aliascomic",
            }),
            expect.objectContaining({
                "X-IG-App-ID": expect.any(String),
                "User-Agent": expect.stringContaining("Chrome"),
            }),
        );
    });

    it("retries transient HTTP, malformed, and network responses", async () => {
        vi.stubEnv("INSTAGRAM_FETCH_ATTEMPTS", "4");
        vi.stubEnv("SOCIAL_REQUEST_DELAY_S", "0.25");
        const networkError = new Error("temporary network failure");
        const fetchProfile = vi
            .fn()
            .mockResolvedValueOnce({ status: 401, body: null })
            .mockResolvedValueOnce({ status: 200, body: { status: "ok" } })
            .mockRejectedValueOnce(networkError)
            .mockResolvedValueOnce(followerResponse(42));
        const sleep = vi.fn().mockResolvedValue(undefined);
        const warn = vi.fn();

        await expect(
            resolveInstagramFollowerCount("retrycomic", {
                fetchProfile,
                sleep,
                warn,
            }),
        ).resolves.toEqual({ status: "resolved", followerCount: 42 });

        expect(fetchProfile).toHaveBeenCalledTimes(4);
        expect(sleep).toHaveBeenCalledTimes(3);
        expect(sleep).toHaveBeenCalledWith(250);
        expect(warn).not.toHaveBeenCalled();
    });

    it("requires two 404 responses before reporting an account as missing", async () => {
        const fetchProfile = vi
            .fn()
            .mockResolvedValueOnce({ status: 404, body: null })
            .mockResolvedValueOnce(followerResponse(77));
        const sleep = vi.fn().mockResolvedValue(undefined);

        await expect(
            resolveInstagramFollowerCount("livecomic", {
                fetchProfile,
                sleep,
            }),
        ).resolves.toEqual({ status: "resolved", followerCount: 77 });

        expect(fetchProfile).toHaveBeenCalledTimes(2);

        fetchProfile.mockReset().mockResolvedValue({ status: 404, body: null });

        await expect(
            resolveInstagramFollowerCount("missingcomic", {
                fetchProfile,
                sleep,
            }),
        ).resolves.toEqual({ status: "not_found" });

        expect(fetchProfile).toHaveBeenCalledTimes(2);
    });

    it("logs one safe structured warning after retries are exhausted", async () => {
        vi.stubEnv("INSTAGRAM_FETCH_ATTEMPTS", "3");
        vi.stubEnv(
            "RESIDENTIAL_PROXY_URL",
            "https://secret-user:secret-password@proxy.example.test",
        );
        const fetchProfile = vi
            .fn()
            .mockRejectedValue(
                new Error(
                    "proxy https://secret-user:secret-password@proxy.example.test failed",
                ),
            );
        const warn = vi.fn();

        await expect(
            resolveInstagramFollowerCount("safecomic", {
                fetchProfile,
                sleep: vi.fn().mockResolvedValue(undefined),
                warn,
            }),
        ).resolves.toEqual({
            status: "failed",
            detail: "Instagram request failed",
        });

        expect(warn).toHaveBeenCalledTimes(1);
        const log = JSON.parse(warn.mock.calls[0][0]);
        expect(log).toEqual({
            level: "warn",
            message: "Instagram follower resolution failed",
            event: "instagram_follower_resolution_failed",
            account: "safecomic",
            attempts: 3,
            failure: "network_error",
            proxyConfigured: true,
        });
        expect(
            JSON.stringify({ log, resolution: "Instagram request failed" }),
        ).not.toContain("secret-user");
        expect(
            JSON.stringify({ log, resolution: "Instagram request failed" }),
        ).not.toContain("secret-password");
    });
});
