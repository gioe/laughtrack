import * as z from "zod";

export const loginSchema = z.object({
    email: z.string()
        .min(1, { message: "This field has to be filled." })
        .email("This is not a valid email."),
    password: z.string().min(8, 'The password must be at least 8 characters long')
        .max(32, 'The password must be a maximun 32 characters')

});
