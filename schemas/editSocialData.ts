import * as z from "zod";

export const editSocialDataSchema = z.object({
    instagram: z.object({
        account: z.string(),
        following: z.number(),
    }),
    tikTok: z.object({
        account: z.string(),
        following: z.number(),
    }),
    twitter: z.object({
        account: z.string(),
        following: z.number(),
    }),
    facebook: z.object({
        account: z.string(),
        following: z.number(),
    }),
    youtube: z.object({
        account: z.string(),
        following: z.number(),
    }),
    website: z.string(),
    cardImage: typeof window === 'undefined' ? z.any() : z.instanceof(FileList).optional().refine((file) => file?.length == 1, 'File is required.'),
    bannerImage: typeof window === 'undefined' ? z.any() : z.instanceof(FileList).optional().refine((file) => file?.length == 1, 'File is required.')

});
