import * as z from "zod";

export const tagEntitySchema = z.object({
    entityName: z.string(),
    tagIds: z.number().array(),
});
