import { SocialDatailInterface } from "../../../../common/interfaces/socialData.interface.js"
import { ISocialData } from "../../../../database/models.js"

export const toSocialDataInterface = (payload: ISocialData): SocialDatailInterface => {
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        website: payload.website
    }
}