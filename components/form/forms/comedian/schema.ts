import * as z from "zod";

export const editComedianSchema = z.object({
    instagram: z.object({
        account: z.string(),
        following: z.string(),
    }).optional(),
    tiktok: z.object({
        account: z.string(),
        following: z.string(),
    }).optional(),
    youtube: z.object({
        account: z.string(),
        following: z.string(),
    }).optional(),
    linktree: z.string().optional(),
    website: z.string().optional(),
    cardImage: typeof window === 'undefined' ? z.any() : z.instanceof(FileList).optional().refine((file) => file?.length == 1, 'File is required.').optional(),
    bannerImage: typeof window === 'undefined' ? z.any() : z.instanceof(FileList).optional().refine((file) => file?.length == 1, 'File is required.').optional(),
    ids: z.number().array().optional(),
});
