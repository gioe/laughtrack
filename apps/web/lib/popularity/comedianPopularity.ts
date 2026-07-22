const SOCIAL_MEDIA_WEIGHT = 0.4;

const SOCIAL_PLATFORMS = {
    instagram: { weight: 0.4, maximumFollowers: 10_000_000 },
    tiktok: { weight: 0.3, maximumFollowers: 50_000_000 },
    youtube: { weight: 0.3, maximumFollowers: 5_000_000 },
} as const;

type SocialFollowers = {
    instagramFollowers: number | null;
    tiktokFollowers: number | null;
    youtubeFollowers: number | null;
};

function socialMediaScore(followers: SocialFollowers) {
    const values = [
        [followers.instagramFollowers, SOCIAL_PLATFORMS.instagram],
        [followers.tiktokFollowers, SOCIAL_PLATFORMS.tiktok],
        [followers.youtubeFollowers, SOCIAL_PLATFORMS.youtube],
    ] as const;

    let weightedScore = 0;
    let weightUsed = 0;

    for (const [followerCount, platform] of values) {
        if (followerCount === null || followerCount <= 0) continue;

        weightedScore +=
            Math.min(followerCount / platform.maximumFollowers, 1) *
            platform.weight;
        weightUsed += platform.weight;
    }

    return weightUsed > 0 ? weightedScore / weightUsed : 0;
}

function roundToFourPlaces(value: number) {
    return Math.round((value + Number.EPSILON) * 10_000) / 10_000;
}

export function recalculatePopularityForInstagramFollowers(input: {
    popularity: number;
    previousInstagramFollowers: number | null;
    nextInstagramFollowers: number | null;
    tiktokFollowers: number | null;
    youtubeFollowers: number | null;
}) {
    const sharedFollowers = {
        tiktokFollowers: input.tiktokFollowers,
        youtubeFollowers: input.youtubeFollowers,
    };
    const previousSocialScore = socialMediaScore({
        ...sharedFollowers,
        instagramFollowers: input.previousInstagramFollowers,
    });
    const nextSocialScore = socialMediaScore({
        ...sharedFollowers,
        instagramFollowers: input.nextInstagramFollowers,
    });

    // Instagram is the only popularity input changed by this admin action.
    // Replace its canonical social contribution while retaining the already
    // persisted performance, podcast, favorite, and other-social signals.
    const nextPopularity =
        input.popularity +
        (nextSocialScore - previousSocialScore) * SOCIAL_MEDIA_WEIGHT;

    return roundToFourPlaces(Math.min(Math.max(nextPopularity, 0), 1));
}
