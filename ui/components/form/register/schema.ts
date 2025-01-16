import { z } from 'zod';

const signupSchema = z.object({
    email: z.string().email(),
    password: z.string().min(8),
    zipCode: z.string().regex(/^\d{5}$/)
});
