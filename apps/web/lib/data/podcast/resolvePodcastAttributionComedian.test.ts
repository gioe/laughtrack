import { describe, expect, it, vi } from "vitest";
import {
    preserveCanonicalComedianProvenance,
    resolvePodcastAttributionComedian,
    type ResolvedPodcastAttributionComedian,
} from "./resolvePodcastAttributionComedian";

type ComedianRow = {
    id: number;
    name: string;
    uuid: string;
    visible: boolean;
    parentComedianId: number | null;
};

function makeReader(rows: ComedianRow[], denied = false) {
    const byId = new Map(rows.map((row) => [row.id, row]));
    return {
        comedian: {
            findUnique: vi.fn(
                async ({ where }: { where: { id: number } }) =>
                    byId.get(where.id) ?? null,
            ),
        },
        $queryRaw: vi.fn().mockResolvedValue(denied ? [{ denied: true }] : []),
    };
}

describe("resolvePodcastAttributionComedian", () => {
    it("follows the full alias chain to a visible canonical comedian", async () => {
        const reader = makeReader([
            {
                id: 3,
                name: "Stage Name",
                uuid: "alias-3",
                visible: true,
                parentComedianId: 2,
            },
            {
                id: 2,
                name: "Middle Alias",
                uuid: "alias-2",
                visible: false,
                parentComedianId: 1,
            },
            {
                id: 1,
                name: "Canonical Comic",
                uuid: "canonical-1",
                visible: true,
                parentComedianId: null,
            },
        ]);

        await expect(
            resolvePodcastAttributionComedian(reader as never, 3),
        ).resolves.toEqual({
            ok: true,
            comedian: {
                id: 1,
                name: "Canonical Comic",
                uuid: "canonical-1",
            },
            requestedComedianId: 3,
            aliasPath: [3, 2, 1],
        });
        expect(reader.$queryRaw).toHaveBeenCalledTimes(1);
    });

    it("rejects hidden and deny-listed canonical comedians", async () => {
        const hiddenReader = makeReader([
            {
                id: 1,
                name: "Hidden Comic",
                uuid: "hidden-1",
                visible: false,
                parentComedianId: null,
            },
        ]);
        const deniedReader = makeReader(
            [
                {
                    id: 2,
                    name: "Denied Comic",
                    uuid: "denied-2",
                    visible: true,
                    parentComedianId: null,
                },
            ],
            true,
        );

        await expect(
            resolvePodcastAttributionComedian(hiddenReader as never, 1),
        ).resolves.toEqual({ ok: false, reason: "hidden" });
        await expect(
            resolvePodcastAttributionComedian(deniedReader as never, 2),
        ).resolves.toEqual({ ok: false, reason: "deny_listed" });
        expect(hiddenReader.$queryRaw).not.toHaveBeenCalled();
    });

    it("rejects missing aliases and cycles", async () => {
        const missingReader = makeReader([]);
        const cycleReader = makeReader([
            {
                id: 1,
                name: "Alias One",
                uuid: "alias-1",
                visible: true,
                parentComedianId: 2,
            },
            {
                id: 2,
                name: "Alias Two",
                uuid: "alias-2",
                visible: true,
                parentComedianId: 1,
            },
        ]);

        await expect(
            resolvePodcastAttributionComedian(missingReader as never, 99),
        ).resolves.toEqual({ ok: false, reason: "not_found" });
        await expect(
            resolvePodcastAttributionComedian(cycleReader as never, 1),
        ).resolves.toEqual({ ok: false, reason: "cycle" });
    });
});

describe("preserveCanonicalComedianProvenance", () => {
    it("preserves every request collapsed onto one canonical comedian", () => {
        const canonical = {
            id: 1,
            name: "Canonical Comic",
            uuid: "canonical-1",
        };
        const resolutions: ResolvedPodcastAttributionComedian[] = [
            {
                ok: true,
                comedian: canonical,
                requestedComedianId: 3,
                aliasPath: [3, 2, 1],
            },
            {
                ok: true,
                comedian: canonical,
                requestedComedianId: 1,
                aliasPath: [1],
            },
        ];

        expect(
            preserveCanonicalComedianProvenance(
                { matchedName: "Stage Name" },
                resolutions,
            ),
        ).toEqual({
            matchedName: "Stage Name",
            canonicalComedianResolution: {
                canonicalComedianId: 1,
                requests: [
                    { requestedComedianId: 3, aliasPath: [3, 2, 1] },
                    { requestedComedianId: 1, aliasPath: [1] },
                ],
            },
        });
    });

    it("leaves evidence unchanged for a direct canonical request", () => {
        const evidence = { provider: "manual" };
        const resolution: ResolvedPodcastAttributionComedian = {
            ok: true,
            comedian: {
                id: 1,
                name: "Canonical Comic",
                uuid: "canonical-1",
            },
            requestedComedianId: 1,
            aliasPath: [1],
        };

        expect(preserveCanonicalComedianProvenance(evidence, resolution)).toBe(
            evidence,
        );
    });
});
