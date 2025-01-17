import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { getClubCount } from "./getClubCount";
import { findClubs } from "./findClubs";
import { Prisma } from "@prisma/client";

export async function getSearchedClubs(
    params: any,
): Promise<ClubSearchResponse> {
    try {
        const [total, data] = await Promise.all([
            getClubCount(params),
            findClubs(params),
        ]);
        return {
            total,
            data,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
