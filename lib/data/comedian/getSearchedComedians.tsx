import { ComedianSearchDTO } from "@/app/api/comedian/search/interface";
import { getComedianCount } from "./getComedianCount";
import { findComedians } from "./findComedians";
import { Prisma } from "@prisma/client";

export async function getSearchedComedians(
    params: any,
): Promise<ComedianSearchDTO> {
    try {
        const [total, data] = await Promise.all([
            getComedianCount(params),
            findComedians(params),
        ]);
        return {
            response: {
                data,
                total,
            },
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
