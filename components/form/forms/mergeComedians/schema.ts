import * as z from "zod";

export const mergeComediansSchema = z.object({
    childComedianId: z.number(),
    parentComedianId: z.number(),
});
