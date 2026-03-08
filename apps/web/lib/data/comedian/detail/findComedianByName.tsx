import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { Prisma } from "@prisma/client";
import { NotFoundError } from "@/objects/NotFoundError";

const COMEDIAN_SELECT = {
    id: true,
    uuid: true,
    name: true,
    linktree: true,
    instagramAccount: true,
    instagramFollowers: true,
    tiktokAccount: true,
    tiktokFollowers: true,
    youtubeAccount: true,
    youtubeFollowers: true,
    website: true,
    popularity: true,
    lineupItems: {
        select: {
            id: true,
        },
        where: {
            show: {
                date: {
                    gt: new Date(),
                },
            },
        },
    },
} as const;

export async function findComedianByName(
    helper: QueryHelper,
): Promise<ComedianDTO> {
    try {
        const name = helper.getSlug();
        if (!name) {
            throw new Error("Comedian name is required");
        }

        const comedianData = await db.comedian.findFirst({
            where: {
                name: {
                    equals: name,
                    mode: Prisma.QueryMode.insensitive,
                },
            },
            select: {
                ...COMEDIAN_SELECT,
                ...(helper.getProfileId()
                    ? {
                          favoriteComedians: {
                              where: {
                                  profileId: helper.getProfileId(),
                              },
                              select: {
                                  id: true,
                              },
                          },
                      }
                    : {}),
            },
        });

        if (!comedianData) {
            throw new NotFoundError(`Comedian with name "${name}" not found`);
        }

        return {
            name: comedianData.name,
            id: comedianData.id,
            imageUrl: buildComedianImageUrl(comedianData.name),
            uuid: comedianData.uuid,
            isFavorite: Boolean(comedianData.favoriteComedians?.length),
            social_data: {
                id: comedianData.id,
                linktree: comedianData.linktree,
                instagram_account: comedianData.instagramAccount,
                instagram_followers: comedianData.instagramFollowers,
                tiktok_account: comedianData.tiktokAccount,
                tiktok_followers: comedianData.tiktokFollowers,
                youtube_account: comedianData.youtubeAccount,
                youtube_followers: comedianData.youtubeFollowers,
                website: comedianData.website,
                popularity: comedianData.popularity,
            },
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findComedianByName:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while fetching comedian details",
        );
    }
}
