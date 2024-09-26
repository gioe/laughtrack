import { ComedianPopularityData } from "../dto/comedian.dto.js";

export const processPopularityData = (popularityScores: ComedianPopularityData[]): number => {
    return popularityScores.map((score: ComedianPopularityData) => {
        const instagramScore = (score.instagramFollowers ?? 0) * 0.8;
        const tikTokScore = (score.tiktokFollowers ?? 0) * 0.9
        const socialScore = (instagramScore + tikTokScore) / 2

        return score.isPseudoynm ? socialScore * 1.5 : socialScore
    })
    .reduce((partialSum, a) => partialSum + a, 0);
}