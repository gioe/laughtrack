import { ComedianDetailsInterface, ComedianInterface } from '../../../common/interfaces/comedian.interface.js'
import { SocialDatailInterface } from '../../../common/interfaces/socialData.interface.js'
import { IComedian, IComedianDetails, IShowDetails, ISocialData } from '../../../database/models.js'
import { toShow, toShowDetails } from '../show/mapper.js'

export const toComedian = (payload: IComedian): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        instagramAccount: payload.instagram_account,
        instagramFollowers: payload.instagram_followers,
        tikTokAccount: payload.tiktok_account,
        tiktokFollowers: payload.tiktok_followers,
        isPseudonym: payload.is_pseudonym,
        website: payload.website,
        poplarityScore: payload.popularity_score
    }
}

export const toComedianDetails = (payload: IComedianDetails): ComedianDetailsInterface => {
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialData(payload.social_data),
        dates: payload.dates.map((show: IShowDetails) => toShowDetails(show))
    }
}

export const toSocialData = (payload: ISocialData): SocialDatailInterface => {
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        website: payload.website
    }
}