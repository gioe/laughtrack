export interface SocialDataInterface {
    instagramAccount?: string;
    tiktokAccount?: string;
    youtubeAccount?: string;
    youtubeFollowers?: number;
    tiktokFollowers?: number;
    instagramFollowers?: number;
    website?: string;
    popularityScore: number;
}

export interface SocialDiscoverable {
    socialData: SocialDataInterface;
}