import * as z from "zod";

export const searchSchema = z.object({
    location: z.string({
        required_error: "Please select a location.",
    }),
    dates: z.object({
        from: z.date(),
        to: z.date(),
    }),
});
