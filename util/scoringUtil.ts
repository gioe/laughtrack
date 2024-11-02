import { GetSocialDataDTO, PopularityScoreIODTO } from "../interfaces";

export const averagePopularityScore = (
    scores: PopularityScoreIODTO[],
): number => {
    if (scores.length == 0) return 0;

    const total = scores
        .map((score: PopularityScoreIODTO) => score.popularity_score)
        .reduce((a: number, b: number) => a + b);
    const average = total / scores.length;

    return Math.floor(average);
};

export const generatePopularityScore = (
    socialData: GetSocialDataDTO,
): number => {
    const instagramScore = (socialData.instagram_followers ?? 0) * 0.6;
    const tiktokScore = (socialData.tiktok_followers ?? 0) * 0.9;
    const youtubeScore = (socialData.youtube_followers ?? 0) * 0.8;

    const socialScore = (instagramScore + tiktokScore + youtubeScore) / 3;

    return Math.floor(socialScore);
};
