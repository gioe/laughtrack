import * as z from "zod";

export const addComedianToShowSchema = z.object({
    showId: z.number(),
    comedians: z.object({
        id: z.number(),
        name: z.string(),
    }).array()
});
