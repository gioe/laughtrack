import * as z from "zod";

export const scrapeClubSchema = z.object({
    entityId: z.number(),
    headless: z.string()
});
