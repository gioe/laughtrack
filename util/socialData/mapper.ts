
import { SocialDataDTO, SocialDataInterface } from "../../objects/class/socialData/socialData.interface";

export const toSocialDataInterface = (
    payload: SocialDataDTO,
): SocialDataInterface => {
    return {
        instagram: {
            following: Number(payload.instagram_followers ?? "0"),
            account: payload.instagram_account ?? ""
        },
        tiktok: {
            following: Number(payload.tiktok_followers ?? "0"),
            account: payload.tiktok_account ?? ""
        },
        youtube: {
            following: Number(payload.youtube_followers ?? "0"),
            account: payload.youtube_account ?? ""
        },
        website: payload.website,
    };
};
