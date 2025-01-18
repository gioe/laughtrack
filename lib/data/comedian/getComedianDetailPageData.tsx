import { findShows } from "../show/findShows";
import { findComedianByName } from "./findComedianByName";
import { getShowCount } from "../show/getCount";
import { Prisma } from "@prisma/client";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";

export async function getComedianDetailPageData(
    params: any,
): Promise<ComedianDetailResponse> {
    try {
        const { name } = params;

        const [comedianData, totalCount, shows] = await Promise.all([
            findComedianByName(params.name),
            getShowCount({
                ...params,
                comedianName: name,
            }),
            findShows({
                ...params,
                comedianName: name,
            }),
        ]);

        return {
            data: comedianData,
            shows,
            total: totalCount,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
