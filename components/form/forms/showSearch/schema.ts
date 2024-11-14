import * as z from "zod";

export const homeSearchSchema = z.object({
    cityId: z.string({
        required_error: "Please select a location.",
    }),
    dates: z.object({
        from: z.date(),
        to: z.date(),
    }),
});
