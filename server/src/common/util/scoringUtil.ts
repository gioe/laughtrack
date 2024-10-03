
export const generateClubPopularityData = (data: any): number => {
    const total = data.scores.map((score: any) => score.popularity_score )

    const average = total / data.scores.length
    return Math.floor(average)
}

export const generateShowPopularityData = (data: any): number => {
    const total = data.scores.map((score: any) => score.popularity_score )

    const average = total / data.scores.length
    return Math.floor(average)
}

export const generateComedianPopularityScore = (popularityData: any): number => {
    const instagramScore = (popularityData.instagram_followers ?? 0) * 0.8;
    const tikTokScore = (popularityData.tiktok_follwers ?? 0) * 0.9
    const socialScore = (instagramScore + tikTokScore) / 2

    const pseudonymScore = popularityData.is_pseudonym ? socialScore * 1.5 : socialScore
    const celebrityHaircut = popularityData.non_comedian ? pseudonymScore / 10 : pseudonymScore

    return Math.floor(celebrityHaircut)
}



