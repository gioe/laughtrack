
// Client
export interface LineupItem {
  id: number;
  name: string;
  popularityScore: number;
}

// DB
export interface CreateLineupItemDTO {
  show_id: number;
  comedian_id: number;
}

export interface LineupItemDTO {
  id: number;
  name: string;
  popularity_score: number;
}

export interface GetLineupItemDTO {
  id: number;
  show_id: number;
  comedian_id: number;
}