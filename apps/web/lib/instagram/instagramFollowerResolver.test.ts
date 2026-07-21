import { describe, expect, it, vi } from "vitest";

import { resolveInstagramFollowerCount } from "./instagramFollowerResolver";

describe("resolveInstagramFollowerCount", () => {
    it("uses the Instagram web profile endpoint and reads the follower count", async () => {
        const fetchProfile = vi.fn().mockResolvedValue({
            status: 200,
            body: {
                data: { user: { edge_followed_by: { count: 123_456 } } },
            },
        });

        await expect(
            resolveInstagramFollowerCount("@aliascomic", { fetchProfile }),
        ).resolves.toEqual({ status: "resolved", followerCount: 123_456 });

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

    it("reports missing accounts and malformed responses", async () => {
        await expect(
            resolveInstagramFollowerCount("missing", {
                fetchProfile: vi
                    .fn()
                    .mockResolvedValue({ status: 404, body: null }),
            }),
        ).resolves.toEqual({ status: "not_found" });

        await expect(
            resolveInstagramFollowerCount("drifted", {
                fetchProfile: vi
                    .fn()
                    .mockResolvedValue({ status: 200, body: { data: {} } }),
            }),
        ).resolves.toEqual({
            status: "failed",
            detail: "Instagram response did not include a follower count",
        });
    });
});
