import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { db } from "@/lib/db";
import { getDiscoveryRailPolicy } from "./getDiscoveryRailPolicy";
import { getDefaultDiscoveryRailPolicy } from "@/lib/discovery/railPolicy";
import { selectDiscoveryPolicyRails } from "@/lib/discovery/railSelector";
import { createOptionalProviderRunner } from "@/lib/discovery/optionalProviders";

vi.mock("@/lib/db", () => ({
    db: { discoveryRailPlatformPolicy: { findUnique: vi.fn() } },
}));

const findUnique = vi.mocked(db.discoveryRailPlatformPolicy.findUnique);
// The rename migration stores catalog 6; do not derive this from app defaults.
function storedPolicy() {
    return {
        platform: "ios",
        catalogVersion: 6,
        policyVersion: 12,
        cycleCadenceHours: 48,
        createdAt: new Date(),
        updatedAt: new Date(),
        updatedByProfileId: null,
        entries: [
            {
                platform: "ios",
                railKey: "shows_tonight",
                enabled: false,
                position: 1,
                rotationPool: null,
                weight: 1,
            },
            {
                platform: "ios",
                railKey: "popular_clubs",
                enabled: true,
                position: 0,
                rotationPool: null,
                weight: 1,
            },
        ],
    };
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.useRealTimers());

describe("getDiscoveryRailPolicy", () => {
    it("loads the migrated catalog and selects stored order and enabled state", async () => {
        findUnique.mockResolvedValue(storedPolicy());
        const observe = vi.fn();
        const policy = await createOptionalProviderRunner()(
            "ios",
            () => getDiscoveryRailPolicy("ios"),
            getDefaultDiscoveryRailPolicy("ios"),
            Date.now() + 150,
            observe,
        );
        expect(observe).toHaveBeenCalledExactlyOnceWith("success");
        expect(findUnique).toHaveBeenCalledWith({
            where: { platform: "ios" },
            include: { entries: true },
        });
        expect(policy).toMatchObject({
            catalogVersion: 6,
            version: 12,
            cycleCadenceHours: 48,
        });
        expect(policy.rails.map((rail) => rail.railKey)).toEqual([
            "popular_clubs",
            "shows_tonight",
        ]);
        expect(
            selectDiscoveryPolicyRails({
                policy,
                actorKey: "anonymous:global",
                cycleIndex: 1,
            }).map((rail) => rail.railKey),
        ).toEqual(["popular_clubs"]);
    });

    it.each(["missing", "invalid", "database"])(
        "preserves safe fallback for %s policy failures",
        async (failure) => {
            if (failure === "missing") findUnique.mockResolvedValue(null);
            else if (failure === "invalid")
                findUnique.mockResolvedValue({
                    ...storedPolicy(),
                    catalogVersion: 999,
                });
            else
                findUnique.mockRejectedValue(new Error("database unavailable"));
            const observe = vi.fn();
            const fallback = getDefaultDiscoveryRailPolicy("ios");
            const result = await createOptionalProviderRunner()(
                "ios",
                () => getDiscoveryRailPolicy("ios"),
                fallback,
                Date.now() + 150,
                observe,
            );
            expect(result).toEqual(fallback);
            expect(observe).toHaveBeenCalledExactlyOnceWith("error");
        },
    );

    it("returns fallback at 150ms and ignores late reader settlement", async () => {
        vi.useFakeTimers();
        let resolve!: (row: ReturnType<typeof storedPolicy>) => void;
        findUnique.mockReturnValue(
            new Promise((done) => {
                resolve = done;
            }) as ReturnType<typeof db.discoveryRailPlatformPolicy.findUnique>,
        );
        const observe = vi.fn();
        const fallback = getDefaultDiscoveryRailPolicy("ios");
        const result = createOptionalProviderRunner()(
            "ios",
            () => getDiscoveryRailPolicy("ios"),
            fallback,
            Date.now() + 150,
            observe,
        );
        await vi.advanceTimersByTimeAsync(149);
        expect(observe).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(await result).toEqual(fallback);
        expect(observe).toHaveBeenCalledExactlyOnceWith("timeout");
        resolve(storedPolicy());
        await vi.advanceTimersByTimeAsync(1);
        expect(observe).toHaveBeenCalledTimes(1);
    });
});
