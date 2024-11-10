import * as z from "zod";

export const clearShowsFromClubSchema = z.object({
    clubId: z.number()
});
