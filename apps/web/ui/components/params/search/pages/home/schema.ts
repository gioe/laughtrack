import * as z from "zod";

export const showSearchFormSchema = z.object({
    distance: z
        .object({
            distance: z.string(),
            zipCode: z
                .string()
                .min(1, "Please enter a city name or zip code")
                .max(60, "Location must be 60 characters or fewer")
                .refine(
                    (v) => /^\d{5}$/.test(v) || /^[A-Za-z]/.test(v),
                    "Please enter a city name (e.g. Chicago or Chicago, IL) or a 5-digit zip code",
                ),
        })
        .required(),
    dates: z
        .object({
            from: z.date({
                required_error: "Start date is required",
                invalid_type_error: "Please select a valid start date",
            }),
            to: z.date({
                required_error: "End date is required",
                invalid_type_error: "Please select a valid end date",
            }),
        })
        .required(),
});
