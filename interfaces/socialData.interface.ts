// Client
export interface SocialDataInterface {
  instagramAccount?: string;
  tiktokAccount?: string;
  youtubeAccount?: string;
  youtubeFollowers?: number;
  tiktokFollowers?: number;
  instagramFollowers?: number;
  website?: string;
  popularityScore?: number;
}

export interface SocialDiscoverable {
  socialData: SocialDataInterface;
}

// DB
export interface UpdateSocialDataDTO {
  instagram_account: string;
  instagram_followers: number;
  tiktok_account: string;
  tiktok_followers: number;
  youtube_account: number;
  youtube_followers: number;
  popularity_score: number;
  website: string;
  id: number
}

export interface GetSocialDataDTO {
  id: number;
  instagram_followers?: number;
  tiktok_followers?: number;
  youtube_followers?: number;
  instagram_account?: string;
  tiktok_account?: string;
  youtube_account?: string;
  website?: string;
}

export interface GroupedPopularityScoreDTO {
  id: number;
  scores: PopularityScoreIODTO[];
}

export interface PopularityScoreIODTO {
  id: number;
  popularity_score: number
}
