import { db } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { createCurationService } from "./decisions";
import { comedianAdapter } from "./comedianAdapter";
// Register domains only after their transactional enforcement is implemented.
// Do not register a no-op adapter: applied means all transactional effects committed.
export const curation = createCurationService({
    store: db,
    adapter: (target) =>
        target.type === "entity" && target.kind === "comedian"
            ? comedianAdapter
            : undefined,
    async invalidate() {
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
