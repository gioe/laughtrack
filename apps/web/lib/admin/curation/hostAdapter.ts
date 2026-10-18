import { Prisma } from "@prisma/client";
import { CurationError, type Adapter } from "./decisions";
export const hostAdapter: Adapter = {
    mode: "immediate",
    async validate(tx, target, _snapshot, command) {
        if (
            target.type !== "relationship" ||
            !["host_of", "cohost_of"].includes(target.kind)
        )
            throw new CurationError(
                "unsupported",
                "Choose a host relationship.",
            );
        if (command.action === "confirm")
            await tx.$queryRaw(
                Prisma.sql`SELECT curation_validate_host(${target.id})`,
            );
    },
    async preview(tx, target, _snapshot, command) {
        const [pair] = await tx.$queryRaw<
            { comedian: string; podcast: string; kind: string }[]
        >(
            Prisma.sql`SELECT s.label comedian,t.label podcast,r.kind FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.id=${target.id}`,
        );
        return [
            `${command.action}: ${pair.comedian} → ${pair.podcast} (${pair.kind === "cohost_of" ? "cohost" : "host"}).`,
            "Apply this pair decision across discovery sources and confirmed aliases; preserve all source evidence.",
            "Other hosts and both entities remain intact. Restore reopens review; it does not confirm attribution.",
        ];
    },
    async apply() {
        /* SQL ledger triggers project all source rows atomically. */
    },
};
