import { PopularityScoreIODTO, GetSocialDataDTO } from "../interfaces/data/socialData.interface.js"


export const averagePopularityScore = (scores: PopularityScoreIODTO[]): number => {
    if (scores.length == 0) return 0

    const total = scores.map((score: PopularityScoreIODTO) => score.popularity_score).reduce((a: number, b: number) => a + b)
    const average = total / scores.length

    return Math.floor(average);
}

export const generatePopularityScore = (socialData: GetSocialDataDTO): number => {
    const instagramScore = (socialData.instagram_followers ?? 0) * 0.8;
    const tikTokScore = (socialData.tikTok_followers ?? 0) * 0.9
    const socialScore = (instagramScore + tikTokScore) / 2

    const pseudonymScore = socialData.is_pseudonym ? socialScore * 1.5 : socialScore
    const celebrityHaircut = socialData.non_comedian ? pseudonymScore / 10 : pseudonymScore

    return Math.floor(celebrityHaircut)
}



