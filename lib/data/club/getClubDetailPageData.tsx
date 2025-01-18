import { getShowCount } from "../show/getCount";
import { findShows } from "../show/findShows";
import { findClubByName } from "./findClubByName";
import { Prisma } from "@prisma/client";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";

export async function getClubDetailPageData(
    params: any,
): Promise<ClubDetailResponse> {
    try {
        const { name } = params;

        const [club, total, dates] = await Promise.all([
            findClubByName(name),
            getShowCount({ ...params, clubName: name }),
            findShows({ ...params, clubName: name }),
        ]);
        return {
            data: club,
            shows: dates,
            total,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
