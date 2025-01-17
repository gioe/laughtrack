import { ClubSearchDTO } from "@/app/api/club/search/interface";
import { getClubCount } from "./getClubCount";
import { findClubs } from "./findClubs";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Prisma } from "@prisma/client";

export async function getSearchedClubs(params: any): Promise<ClubSearchDTO> {
    try {
        const [total, data] = await Promise.all([
            getClubCount(params),
            findClubs(params),
        ]);
        return {
            response: {
                total,
                data,
            },
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
