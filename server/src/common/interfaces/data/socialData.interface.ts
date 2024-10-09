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
  popularity_score?: number
}

export interface GroupedPopularityScoreDTO {
  id: number;
  scores: PopularityScoreIODTO[];
}

export interface PopularityScoreIODTO {
  id: number;
  popularity_score: number
}