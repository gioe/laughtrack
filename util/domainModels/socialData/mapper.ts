import {
    GetSocialDataDTO,
    GroupedPopularityScoreDTO,
    PopularityScoreIODTO,
    SocialDataInterface,
    UpdateSocialDataDTO
} from "../../../interfaces"
import { averagePopularityScore, generatePopularityScore } from "../../scoringUtil"

export const toSocialDataInterface = (payload: GetSocialDataDTO): SocialDataInterface => {
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        youtubeAccount: payload.youtube_account,
        youtubeFollowers: payload.youtube_followers,
        website: payload.website
    }
}

export const toUpdateSocialDataDTO = (payload: any): UpdateSocialDataDTO => {
    const { instagramAccount, instagramFollowers, youtubeAccount, youtubeFollowers, tiktokAccount, tiktokFollowers, website, id } = payload;

    const instagramFollowerInt = parseInt(instagramFollowers as string)
    const tiktokFollowerInt = parseInt(tiktokFollowers as string)
    const youtubeFollowerInt = parseInt(youtubeFollowers as string)
    const instagramFollowerCount = !isNaN(instagramFollowerInt) ? instagramFollowerInt : 0;
    const tiktokFollowerCount = !isNaN(tiktokFollowerInt) ? tiktokFollowerInt : 0;
    const youtubeFollowerCount = !isNaN(youtubeFollowerInt) ? youtubeFollowerInt : 0;
    const idNumber = parseInt(id as string)
    
    const popularityScore = generatePopularityScore({
        id: idNumber,
        instagram_followers: instagramFollowerCount,
        tiktok_followers: tiktokFollowerCount,
        youtube_followers: youtubeFollowerCount
    })


    return {
        id: idNumber,
        instagram_followers: instagramFollowerCount,
        tiktok_followers: tiktokFollowerCount,
        youtube_followers: youtubeFollowerCount,
        popularity_score: popularityScore,
        instagram_account: instagramAccount,
        youtube_account: youtubeAccount,
        tiktok_account: tiktokAccount,
        website: website
    }
}

export const toPopularityScores = (payload: GroupedPopularityScoreDTO[] | GetSocialDataDTO[]): PopularityScoreIODTO[] => {
    return payload.map((data: any) => toPopularityScore(data))
}

export const toPopularityScore = (payload: any): PopularityScoreIODTO => {
    return {
        id: payload.id,
        popularity_score: payload.scores ? averagePopularityScore(payload.scores) : generatePopularityScore(payload)
    }
}


