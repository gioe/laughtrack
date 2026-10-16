import { Prisma } from "@prisma/client";
import { CurationError, type Adapter } from "./decisions";
export const podcastAdapter: Adapter = {
    mode: "immediate",
    async validate(tx, target, _snapshot, command) {
        if (
            target.type !== "entity" ||
            target.kind !== "podcast" ||
            target.scope !== "entity"
        )
            throw new CurationError(
                "unsupported",
                "Choose a podcast identity.",
            );
        if (command.action !== "approve") return;
        const [row] = await tx.$queryRaw<any[]>(Prisma.sql`
            SELECT q.* FROM curation_entities e JOIN podcasts p ON p.id=e.podcast_id
            CROSS JOIN LATERAL curation_podcast_policy(to_jsonb(p)) q
            WHERE e.id=${target.id} AND length(btrim(p.title))>0`);
        if (
            !row ||
            row.entity_id !== target.id ||
            row.disposition !== "pending"
        )
            throw new CurationError(
                "identity_conflict",
                "Review podcast metadata and resolve any identity conflict or block before approving.",
            );
    },
    async preview(_tx, _target, _snapshot, command) {
        return [
            command.action === "block"
                ? "Hide this podcast and its episodes; stop discovery, refresh and episode ingestion for all known provider and feed identities. Keep existing records and host decisions."
                : command.action === "restore"
                  ? "Return this podcast to pending review. Do not publish it or revive rejected host relationships."
                  : "Approve this podcast for episode ingestion. Public listing also requires an accepted eligible host or cohost.",
        ];
    },
    async apply() {
        /* The database policy reads the committed ledger atomically. */
    },
};
