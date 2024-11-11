import {
    GroupedSocialDataDTO,
    PopularityScoreIODTO,
    SocialDataDTO,
    SocialDataInterface,
} from "../../objects/interfaces";
import {
    averagePopularityScore,
    generatePopularityScore,
} from ".";

export const toSocialDataInterface = (
    payload: SocialDataDTO,
): SocialDataInterface => {
    return {
        instagramFollowers: payload.instagram_followers,
        instagramAccount: payload.instagram_account,
        tiktokFollowers: payload.tiktok_followers,
        tiktokAccount: payload.tiktok_account,
        youtubeAccount: payload.youtube_account,
        youtubeFollowers: payload.youtube_followers,
        website: payload.website,
    };
};


export const toPopularityScores = (
    payload: GroupedSocialDataDTO[] | SocialDataDTO[],
): PopularityScoreIODTO[] => {
    return payload.map((data: any) => toPopularityScore(data));
};

export const toPopularityScore = (payload: any): PopularityScoreIODTO => {
    return {
        id: payload.id,
        popularity_score: payload.scores
            ? averagePopularityScore(payload.scores)
            : generatePopularityScore(payload),
    };
};
