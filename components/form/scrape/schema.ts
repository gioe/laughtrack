import * as z from "zod";

export const scrapeClubSchema = z.object({
    entityIdentifier: z.string(),
    headless: z.string(),
    pause: z.string(),
});
