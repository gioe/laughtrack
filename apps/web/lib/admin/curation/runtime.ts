import { db } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { createCurationService } from "./decisions";
// Deliberately empty until each migration and domain adapter is implemented.
// Do not register a no-op adapter: applied means all transactional effects committed.
export const curation = createCurationService({
    store: db,
    adapter: () => undefined,
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
