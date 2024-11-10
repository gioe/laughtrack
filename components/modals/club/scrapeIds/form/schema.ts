import * as z from "zod";

export const scrapeClubSelectionMenuSchema = z.object({
    clubIds: z.number().array(),
    headless: z.boolean(),
});
