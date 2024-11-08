// Client
export interface SocialDataInterface {
    instagram?: SocialMediaAccount;
    tiktok?: SocialMediaAccount;
    youtube?: SocialMediaAccount;
    facebook?: SocialMediaAccount;
    twitter?: SocialMediaAccount;
    website?: string;
    popularityScore?: number;
}

export interface SocialMediaAccount {
    account: string,
    following: number;
}

export interface SocialDiscoverable {
    socialData?: SocialDataInterface;
}

// DTO
export interface SocialDataDTO {
    id: number;
    instagram_followers?: number;
    tiktok_followers?: number;
    youtube_followers?: number;
    instagram_account?: string;
    tiktok_account?: string;
    youtube_account?: string;
    website?: string;
    popularity_score?: number;
}

export interface GroupedSocialDataDTO {
    id: number;
    scores: PopularityScoreIODTO[];
}

export interface PopularityScoreIODTO {
    id: number;
    popularity_score: number;
}
