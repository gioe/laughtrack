import { Prisma } from "@prisma/client";

type PodcastAttributionComedianReader = Pick<
    Prisma.TransactionClient,
    "comedian" | "$queryRaw"
>;

type ResolvedComedian = {
    id: number;
    name: string;
    uuid: string;
};

export type PodcastAttributionComedianResolution =
    | {
          ok: true;
          comedian: ResolvedComedian;
          requestedComedianId: number;
          aliasPath: number[];
      }
    | {
          ok: false;
          reason: "not_found" | "cycle" | "hidden" | "deny_listed";
      };

export type ResolvedPodcastAttributionComedian = Extract<
    PodcastAttributionComedianResolution,
    { ok: true }
>;

export async function resolvePodcastAttributionComedian(
    tx: PodcastAttributionComedianReader,
    requestedComedianId: number,
): Promise<PodcastAttributionComedianResolution> {
    const aliasPath: number[] = [];
    const seen = new Set<number>();
    let comedianId = requestedComedianId;

    while (true) {
        if (seen.has(comedianId)) {
            return { ok: false, reason: "cycle" };
        }
        seen.add(comedianId);
        aliasPath.push(comedianId);

        const comedian = await tx.comedian.findUnique({
            where: { id: comedianId },
            select: {
                id: true,
                name: true,
                uuid: true,
                visible: true,
                parentComedianId: true,
            },
        });
        if (!comedian) {
            return { ok: false, reason: "not_found" };
        }
        if (comedian.parentComedianId != null) {
            comedianId = comedian.parentComedianId;
            continue;
        }
        if (comedian.visible === false) {
            return { ok: false, reason: "hidden" };
        }

        const denied = await tx.$queryRaw<Array<{ denied: boolean }>>`
            SELECT TRUE AS denied
            FROM comedian_deny_list
            WHERE lower(btrim(regexp_replace(replace(name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                  lower(btrim(regexp_replace(replace(${comedian.name}, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
            LIMIT 1
        `;
        if (denied.length > 0) {
            return { ok: false, reason: "deny_listed" };
        }

        return {
            ok: true,
            comedian: {
                id: comedian.id,
                name: comedian.name,
                uuid: comedian.uuid,
            },
            requestedComedianId,
            aliasPath,
        };
    }
}

export function preserveCanonicalComedianProvenance(
    evidence: Prisma.InputJsonValue,
    resolution:
        | ResolvedPodcastAttributionComedian
        | readonly ResolvedPodcastAttributionComedian[],
): Prisma.InputJsonValue {
    const resolutions = Array.isArray(resolution) ? resolution : [resolution];
    if (resolutions.length === 0) {
        return evidence;
    }

    const canonicalComedianId = resolutions[0].comedian.id;
    if (
        resolutions.some(
            (candidate) => candidate.comedian.id !== canonicalComedianId,
        )
    ) {
        throw new Error(
            "Canonical comedian provenance cannot combine different comedians",
        );
    }
    if (
        resolutions.every(
            (candidate) =>
                candidate.requestedComedianId === candidate.comedian.id,
        )
    ) {
        return evidence;
    }

    const provenance = {
        canonicalComedianId,
        requests: resolutions.map((candidate) => ({
            requestedComedianId: candidate.requestedComedianId,
            aliasPath: candidate.aliasPath,
        })),
    };
    if (
        typeof evidence === "object" &&
        evidence !== null &&
        !Array.isArray(evidence)
    ) {
        return {
            ...evidence,
            canonicalComedianResolution: provenance,
        };
    }
    return {
        originalEvidence: evidence,
        canonicalComedianResolution: provenance,
    };
}
