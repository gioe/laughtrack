import { getComedianCount } from "./getComedianCount";
import { findComedians } from "./findComedians";
import { Prisma } from "@prisma/client";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";

export async function getSearchedComedians(
    params: any,
): Promise<ComedianSearchResponse> {
    try {
        const [total, data] = await Promise.all([
            getComedianCount(params),
            findComedians(params),
        ]);
        return {
            data,
            total,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
