import { ComedianInterface } from '../../../common/interfaces/comedian.interface.js'
import { IComedian } from '../../../database/models.js'

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
