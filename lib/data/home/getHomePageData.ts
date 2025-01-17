import { HomePageDataResponse } from "@/app/api/home/interface";
import { getPopularClubs } from "./getPopularClubs";
import { getTrendingComedians } from "./getTrendingComedians";
import { Prisma } from "@prisma/client";

export async function getHomePageData(userId?: string): Promise<HomePageDataResponse> {
    try {
        const [comedians, clubs] = await Promise.all([getTrendingComedians(userId), getPopularClubs(userId)])
        return {
            comedians,
            clubs,
        };
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }

}
