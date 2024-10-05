export interface CreateLineupItemDTO {
  show_id: number;
  comedian_id: number;
}

export interface LineupItemDTO {
  id: number;
  name: string;
  popularity_score: number;
}