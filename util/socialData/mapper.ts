/* eslint-disable @typescript-eslint/no-explicit-any */
import {
    GroupedSocialDataDTO,
    PopularityScoreIODTO,
    SocialDataDTO,
    SocialDataInterface,
} from "../../objects/interface";
import {
    averagePopularityScore,
    generatePopularityScore,
} from ".";

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
