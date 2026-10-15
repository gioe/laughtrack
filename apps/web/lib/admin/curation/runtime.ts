import { db } from "@/lib/db";
import { revalidatePath, revalidateTag } from "next/cache";
import { createCurationService } from "./decisions";
import { showAdapter } from "./showAdapter";
import { clubAdapter } from "./clubAdapter";
import { comedianAdapter } from "./comedianAdapter";
// Register domains only after their transactional enforcement is implemented.
// Do not register a no-op adapter: applied means all transactional effects committed.
export const curation = createCurationService({
    store: {
        $queryRaw: (query) => db.$queryRaw(query),
        $transaction: (fn) =>
            db.$transaction(async (tx) => {
                // Acquire the shared intake lock before entity row locks, matching
                // scraper/ledger triggers and avoiding lock-order inversion.
                await tx.$queryRaw`SELECT curation_lock_intake()`;
                return fn(tx);
            }),
    },
    adapter: (target) =>
        target.type === "entity" && target.kind === "show"
            ? showAdapter
            : target.type === "entity" && target.kind === "club"
              ? clubAdapter
              : target.type === "entity" && target.kind === "comedian"
                ? comedianAdapter
                : undefined,
    async invalidate() {
        revalidateTag("show-detail-data");
        revalidateTag("show-metadata");
        revalidateTag("club-detail-data");
        revalidateTag("club-metadata");
        for (const path of [
            "/admin",
            "/comedian",
            "/club",
            "/show",
            "/podcast",
        ])
            revalidatePath(path, "layout");
    },
});
