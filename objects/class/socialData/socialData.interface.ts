import { SocialData } from "./SocialData";

// Client
export interface SocialDataInterface {
    instagram?: SocialMediaAccountInterface;
    tiktok?: SocialMediaAccountInterface;
    youtube?: SocialMediaAccountInterface;
    facebook?: SocialMediaAccountInterface;
    twitter?: SocialMediaAccountInterface;
    website?: string;
    popularityScore: number | null;
    linktree?: string
}

export interface SocialMediaAccountInterface {
    account: string | null,
    following: number;
}

export interface SocialDiscoverable {
    socialData?: SocialData;
}

// DTO
export interface SocialDataDTO {
    id: number;
    instagram_followers: number | null;
    tiktok_followers: number | null;
    youtube_followers: number | null;
    instagram_account: string | null;
    tiktok_account: string | null;
    youtube_account: string | null;
    website: string | null;
    popularity: number | null;
    linktree: string | null;
}

export interface SocialMediaAccountDTO {
    account: string,
    following: number;
}

export interface GroupedSocialDataDTO {
    id: number;
    scores: PopularityScoreIODTO[];
}

export interface PopularityScoreIODTO {
    id: number;
    popularity: number;
}
