import { SocialDataInterface } from "../../../interfaces/client/socialData.interface.js"
import { GetSocialDataDTO, GroupedPopularityScoreDTO, PopularityScoreIODTO } from "../../../interfaces/data/socialData.interface.js"
import { averagePopularityScore, generatePopularityScore } from "../../scoringUtil.js"

export const toSocialDataInterface = (payload: GetSocialDataDTO | undefined | null): SocialDataInterface | undefined => {
    if (payload == undefined || payload == null) return undefined
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        youtubeAccount: payload.youtube_account,
        youtubeFollowers: payload.youtube_followers,
        website: payload.website,
        popularityScore: payload.popularity_score ?? 0
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

