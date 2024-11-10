import * as z from "zod";

export const tagEntitySchema = z.object({
    entityId: z.number(),
    tagIds: z.number().array(),
});
