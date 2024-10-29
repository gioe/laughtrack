export interface Favoritable {
  id: number;
  name: string;
  isFavorite: boolean;
}

// DB
export interface CreateFavoriteDTO {
  id: number;
  user_id: number;
}