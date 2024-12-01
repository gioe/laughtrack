import { SocialData } from "./SocialData";

// Client
export interface SocialDataInterface {
    instagram?: SocialMediaAccountInterface;
    tiktok?: SocialMediaAccountInterface;
    youtube?: SocialMediaAccountInterface;
    facebook?: SocialMediaAccountInterface;
    twitter?: SocialMediaAccountInterface;
    website?: string;
    popularityScore?: number;
    linktree?: string
}

export interface SocialMediaAccountInterface {
    account?: string,
    following: number;
}

export interface SocialDiscoverable {
    socialData?: SocialData;
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
    popularity?: number;
    linktree?: string
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
