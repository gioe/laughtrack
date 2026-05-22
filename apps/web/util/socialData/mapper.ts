
import { SocialDataDTO, SocialDataInterface } from "../../objects/class/socialData/socialData.interface";

export const toSocialDataInterface = (
    payload: SocialDataDTO,
): SocialDataInterface => {
    return {
        instagram: {
            following: Number(payload.instagramFollowers ?? "0"),
            account: payload.instagramAccount ?? ""
        },
        tiktok: {
            following: Number(payload.tiktokFollowers ?? "0"),
            account: payload.tiktokAccount ?? ""
        },
        youtube: {
            following: Number(payload.youtubeFollowers ?? "0"),
            account: payload.youtubeAccount ?? ""
        },
        linktree: payload.linktree ?? "",
        website: payload.website ?? "",
        popularityScore: 0
    };
};
