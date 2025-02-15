import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { findComedianByName } from "./findComedianByName";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { EntityResponseDTO } from "@/objects/interface/paginatedEntity.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ParameterizedRequestData } from "@/objects/interface";

export type ComedianDetailResponse = EntityResponseDTO<ComedianDTO>;

export async function getComedianDetailPageData(
    requestData: ParameterizedRequestData,
): Promise<ComedianDetailResponse> {
    try {
        const helper = await QueryHelper.storePageParams(
            new URLSearchParams(requestData.params),
        );

        const [comedianData, showsWithCount, filters] = await Promise.all([
            findComedianByName(helper),
            findShowsWithCount(helper),
            getFilters(EntityType.Show, helper),
        ]);

        return {
            data: comedianData,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
