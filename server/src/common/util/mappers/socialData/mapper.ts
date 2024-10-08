import { SocialDataInterface } from "../../../interfaces/client/socialData.interface.js"
import { GroupedPopularityScoreDTO, GetSocialDataDTO, PopularityScoreIODTO } from "../../../interfaces/data/socialData.interface.js"
import { averagePopularityScore, generatePopularityScore } from "../../scoringUtil.js"

export const toSocialDataInterface = (payload?: any): SocialDataInterface | undefined => {
    if (payload == undefined) return undefined
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        website: payload.website,
        isPseudonym: payload.is_pseudonym,
        nonComedian: payload.non_comedian,
        popularityScore: payload.popularity_score
    }
}

export const toPopularityScores = (payload: GetSocialDataDTO[] | null): PopularityScoreIODTO[] => {
    return payload == null ? [] : payload.map((data: any) => toPopularityScore(data))
}

export const toPopularityScore = (payload: GetSocialDataDTO): PopularityScoreIODTO => {
    return {
        id: payload.id,
        popularity_score: generatePopularityScore(payload)
    }
}

export const flattenScoreCollections = (response: GroupedPopularityScoreDTO[] | null): PopularityScoreIODTO[] => {
    if (response == null) return []
    return response.map((item: GroupedPopularityScoreDTO) => {
        return {
            id: item.id,
            popularity_score: averagePopularityScore(item.scores)
        } as PopularityScoreIODTO
    })
}

