import { buildClubImageUrl } from "@/util/imageUtil";
import { getShowCount } from "../show/getCount";
import { findShows } from "../show/findShows";
import { findClubByName } from "./findClubByName";
import { ClubDetailDTO } from "@/app/api/club/[name]/interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Prisma } from "@prisma/client";

export async function getClubDetailPageData(
    params: any,
): Promise<ClubDetailDTO> {
    try {
        const { name } = params;

        const [club, total, dates] = await Promise.all([
            findClubByName(name),
            getShowCount({ ...params, clubName: name }),
            findShows({ ...params, clubName: name }),
        ]);

        return {
            response: {
                data: {
                    ...club,
                    dates,
                },
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
