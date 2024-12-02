import * as z from "zod";

export const clearShowsFromClubSchema = z.object({
    clubName: z.string()
});
