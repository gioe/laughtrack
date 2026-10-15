import { unstable_cache, unstable_noStore } from "next/cache";
import { db } from "@/lib/db";

/** Read the suppression revision outside Next's data cache. Worker decisions
 * therefore invalidate public page data without making an HTTP callback. */
export function publicationCache<T extends (...args: any[]) => Promise<any>>(
    callback: T,
    keyParts: string[] = [],
    options?: Parameters<typeof unstable_cache>[2],
): T {
    return (async (...args: Parameters<T>) => {
        unstable_noStore();
        const [state] = await db.$queryRaw<{ revision: bigint }[]>`
            SELECT revision FROM show_publication_revision WHERE id=1`;
        if (!state) throw new Error("Show publication state unavailable");
        return unstable_cache(
            callback,
            [...keyParts, `publication:${state.revision}`],
            options,
        )(...args);
    }) as T;
}
