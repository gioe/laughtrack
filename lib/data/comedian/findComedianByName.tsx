import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";

export async function findComedianByName(name: string): Promise<ComedianDTO> {
    const comedianData = await db.comedian.findFirst({
        where: {
            name,
        },
        select: {
            id: true,
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
        },
    });

    if (!comedianData) {
        throw new Error(`Comedian with name ${name} not found`);
    }

    return {
        name: comedianData.name,
        id: comedianData.id,
        imageUrl: buildComedianImageUrl(comedianData.name),
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
}
