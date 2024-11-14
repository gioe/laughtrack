import * as z from "zod";

export const scrapeEntitySelectionMenuSchema = z.object({
    entityType: z.string(),
    ids: z.number().array(),
    headless: z.boolean(),
});
