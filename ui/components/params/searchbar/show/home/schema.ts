import * as z from "zod";

export const showSearchFormSchema = z.object({
    distance: z.object({
        distance: z.string(),
        zipCode: z.string()
            .min(5, "Zip code must be 5 digits")
            .max(5, "Zip code must be 5 digits")
            .regex(/^[0-9]{5}$/, "Please enter a valid zip code"),
    }),
    dates: z.object({
        from: z.date({
            required_error: "Start date is required",
            invalid_type_error: "Please select a valid start date",
        }),
        to: z.date({
            required_error: "End date is required",
            invalid_type_error: "Please select a valid end date",
        })
    })
});
