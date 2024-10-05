
export interface PopularityScoreDTO {
    id?: number;
    popularity_score?: number
  }

export interface GroupedPopularityScores {
    id: number;
    scores: PopularityScoreDTO[];
}  