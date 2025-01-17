import { getShowCount } from "./getCount"
import { findShows } from "./findShows"
import { Prisma } from "@prisma/client";

export async function getSearchedShows(params: any) {
    try {
        const [total, data] = await Promise.all([getShowCount(params), findShows(params)])

        return {
            total,
            data
        }
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }

}
