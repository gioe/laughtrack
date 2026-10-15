import { db } from "@/lib/db";
import { revalidatePath, revalidateTag } from "next/cache";
import { createCurationService } from "./decisions";
import { clubAdapter } from "./clubAdapter";
import { comedianAdapter } from "./comedianAdapter";
// Register domains only after their transactional enforcement is implemented.
// Do not register a no-op adapter: applied means all transactional effects committed.
export const curation = createCurationService({
    store: db,
    adapter: (target) =>
        target.type === "entity" && target.kind === "club"
            ? clubAdapter
            : target.type === "entity" && target.kind === "comedian"
              ? comedianAdapter
              : undefined,
    async invalidate() {
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
