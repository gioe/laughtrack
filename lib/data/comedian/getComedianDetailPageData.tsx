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
        // Get comedian data
        const comedianData = await findComedianByName(params.name);
        const totalCount = await getShowCount({
            ...params,
            comedianName: name,
        });

        // First get all relevant shows
        const relevantShows = await findShows(params);

        const showIds = relevantShows.map((show) => show.id);

        // Get detailed show data
        const dates = await findShows({ ...params, showIds });

        return {
            data: {
                ...comedianData,
                dates,
            },
            total: totalCount,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
