
export interface GetSocialDataDTO {
  id: number;
  instagram_followers?: number;
  tikTok_followers?: number;
  is_pseudonym?: boolean
  non_comedian?: boolean;
}

export interface GroupedPopularityScoreDTO {
  id: number;
  scores: PopularityScoreIODTO[];
}

export interface PopularityScoreIODTO {
  id: number;
  popularity_score: number
}