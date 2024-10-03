import { SocialDataInterface } from "../../../interfaces/client/socialData.interface.js"
import { PopularityScoreDTO } from "../../../interfaces/data/popularityScore.interface.js"
import { generateClubPopularityData } from "../../scoringUtil.js"

export const toSocialDataInterface = (payload: any): SocialDataInterface => {
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        website: payload.website,
        isPseudonym: payload.is_pseudonym,
        nonComedian: payload.non_comedian
    }
}

export const toPopularityScores = (payload: any | null): PopularityScoreDTO[] | null => {
    if (payload == null) return null
    return payload.map((data: any) => toPopularityScore(data))
}


export const toPopularityScore = (payload: any): PopularityScoreDTO => {
    return {
        id: payload.id,
        popularity_score: generateClubPopularityData(payload)
    }
}