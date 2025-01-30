import { z } from 'zod';

export const registerSchema = z.object({
    email: z.string().email(),
    password: z.string().min(8),
    zipCode: z.string().regex(/^\d{5}$/),
    emailOptIn: z.boolean().default(false)
});
